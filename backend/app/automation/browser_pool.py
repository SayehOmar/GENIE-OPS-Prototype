"""
Browser worker pool manager for process isolation.

Manages a pool of browser worker processes to avoid Windows threading issues.
Provides async interface compatible with existing code.
"""
import os
import sys
import asyncio
import uuid
import platform
from typing import Dict, Optional, Any
from multiprocessing import Process, Queue, Manager
from app.core.config import settings
from app.automation.commands import BrowserCommand, BrowserResult
from app.automation.browser_worker import worker_main
from app.utils.logger import logger


class BrowserWorkerPool:
    """
    Manages a pool of browser worker processes.
    
    Each worker runs in a separate process with its own Playwright instance,
    avoiding Windows threading issues. The pool distributes browser operations
    across available workers.
    """
    
    def __init__(
        self,
        pool_size: Optional[int] = None,
        use_pool: Optional[bool] = None
    ):
        """
        Initialize the browser worker pool.
        
        Args:
            pool_size: Number of worker processes (default: from config or 3)
            use_pool: Whether to use worker pool (default: True on Windows, False otherwise)
        """
        # Determine if we should use the pool
        if use_pool is None:
            # Check config first, then default based on platform
            config_use_pool = getattr(settings, 'BROWSER_USE_WORKER_POOL', None)
            if config_use_pool is not None:
                self.use_pool = config_use_pool
            else:
                # Default to True on Windows, False on other platforms
                self.use_pool = platform.system() == "Windows"
        else:
            self.use_pool = use_pool
        
        self.pool_size = pool_size or getattr(settings, 'BROWSER_WORKER_POOL_SIZE', 3)
        
        # Validate pool size matches workflow max_concurrent (recommended)
        workflow_max_concurrent = getattr(settings, 'WORKFLOW_MAX_CONCURRENT', 3)
        if self.pool_size != workflow_max_concurrent:
            logger.warning(
                f"Browser pool size ({self.pool_size}) doesn't match "
                f"WORKFLOW_MAX_CONCURRENT ({workflow_max_concurrent}). "
                f"Consider setting BROWSER_WORKER_POOL_SIZE={workflow_max_concurrent}"
            )
        
        self.workers: list[Process] = []
        self.command_queues: list[Queue] = []
        self.result_queues: list[Queue] = []
        self.pending_results: Dict[str, asyncio.Future] = {}
        self.worker_index = 0
        self.is_running = False
        self.manager = None
        # Session-based worker assignment: map session_id -> worker_index
        self.session_workers: Dict[str, int] = {}
        # Session-based worker assignment: map session_id -> worker_index
        self.session_workers: Dict[str, int] = {}
        
        logger.info(
            f"BrowserWorkerPool initialized: use_pool={self.use_pool}, "
            f"pool_size={self.pool_size}, platform={platform.system()}"
        )
    
    def start(self):
        """
        Start the worker pool by spawning worker processes.
        """
        if not self.use_pool:
            logger.info("Browser worker pool disabled, using direct Playwright")
            return
        
        if self.is_running:
            logger.warning("Browser worker pool is already running")
            return
        
        try:
            # On Windows, multiprocessing requires proper setup
            import platform
            if platform.system() == "Windows":
                # Use spawn method for Windows (more reliable)
                import multiprocessing
                if multiprocessing.get_start_method(allow_none=True) != "spawn":
                    try:
                        multiprocessing.set_start_method("spawn", force=True)
                    except RuntimeError:
                        # Already set, ignore
                        pass
            
            # Create manager for shared state if needed
            self.manager = Manager()
            
            # Create queues for each worker
            for i in range(self.pool_size):
                command_queue = Queue()
                result_queue = Queue()
                self.command_queues.append(command_queue)
                self.result_queues.append(result_queue)
                
                # Spawn worker process
                # Use spawn context for Windows compatibility
                import multiprocessing
                ctx = multiprocessing.get_context("spawn")
                worker = ctx.Process(
                    target=worker_main,
                    args=(command_queue, result_queue, i),
                    daemon=True
                )
                worker.start()
                self.workers.append(worker)
                logger.info(f"Browser worker {i} started (PID: {worker.pid})")
            
            # Give workers a moment to initialize
            import time
            time.sleep(0.5)
            
            # Verify workers are still alive
            dead_workers = [i for i, w in enumerate(self.workers) if not w.is_alive()]
            if dead_workers:
                logger.error(f"Workers {dead_workers} died during startup")
                self.cleanup()
                raise RuntimeError(f"Failed to start {len(dead_workers)} worker(s)")
            
            self.is_running = True
            logger.info(f"Browser worker pool started with {self.pool_size} workers")
        
        except Exception as e:
            logger.error(f"Failed to start browser worker pool: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()
            raise
    
    def stop(self):
        """
        Stop the worker pool and terminate all worker processes.
        """
        if not self.is_running:
            return
        
        logger.info("Stopping browser worker pool...")
        
        # Send shutdown signal to all workers
        for command_queue in self.command_queues:
            try:
                command_queue.put(None)  # None signals shutdown
            except Exception as e:
                logger.warning(f"Error sending shutdown signal: {e}")
        
        # Wait for workers to terminate
        for i, worker in enumerate(self.workers):
            try:
                worker.join(timeout=5.0)  # Wait up to 5 seconds
                if worker.is_alive():
                    logger.warning(f"Worker {i} did not terminate gracefully, forcing termination")
                    worker.terminate()
                    worker.join(timeout=2.0)
                    if worker.is_alive():
                        worker.kill()
            except Exception as e:
                logger.error(f"Error stopping worker {i}: {e}")
        
        self.cleanup()
        logger.info("Browser worker pool stopped")
    
    def cleanup(self):
        """Clean up resources"""
        self.workers.clear()
        self.command_queues.clear()
        self.result_queues.clear()
        self.pending_results.clear()
        self.is_running = False
        if self.manager:
            self.manager.shutdown()
            self.manager = None
    
    def _get_next_worker(self, session_id: Optional[str] = None) -> int:
        """
        Get the next worker index using session-based assignment or round-robin.
        Skips dead workers automatically.
        
        Args:
            session_id: Optional session ID to use the same worker for a workflow.
                       If provided, returns the same worker for this session.
        
        Returns:
            Worker index to use (guaranteed to be alive)
            
        Raises:
            RuntimeError: If no alive workers are available
        """
        # Find alive workers
        alive_workers = [i for i, w in enumerate(self.workers) if w.is_alive()]
        
        if not alive_workers:
            raise RuntimeError("No alive workers available in pool")
        
        # If session_id provided, try to reuse the same worker
        if session_id and session_id in self.session_workers:
            assigned_worker = self.session_workers[session_id]
            if assigned_worker in alive_workers:
                # Worker is still alive, reuse it
                logger.debug(f"Reusing worker {assigned_worker} for session {session_id[:8]}...")
                return assigned_worker
            else:
                # Worker died, assign a new one
                logger.warning(f"Session {session_id[:8]}... worker {assigned_worker} died, reassigning")
                del self.session_workers[session_id]
        
        # Round-robin assignment for new sessions
        # If current worker is dead, find next alive one
        if self.worker_index not in alive_workers:
            self.worker_index = alive_workers[0]
        
        # Get current worker
        index = self.worker_index
        
        # Find next alive worker
        current_pos = alive_workers.index(index)
        next_pos = (current_pos + 1) % len(alive_workers)
        self.worker_index = alive_workers[next_pos]
        
        # Store session assignment if provided
        if session_id:
            self.session_workers[session_id] = index
            logger.debug(f"Assigned worker {index} to session {session_id[:8]}...")
        
        return index
    
    async def execute_command(
        self,
        command_type: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        session_id: Optional[str] = None
    ) -> BrowserResult:
        """
        Execute a browser command through the worker pool.
        
        Args:
            command_type: Type of command (navigate, fill_form, etc.)
            params: Command parameters
            timeout: Timeout in seconds (default: from config or 60)
            session_id: Optional session ID to use the same worker for a workflow
            
        Returns:
            BrowserResult with command execution result
            
        Raises:
            RuntimeError: If pool is not running or worker is dead
        """
        if not self.use_pool or not self.is_running:
            raise RuntimeError("Browser worker pool is not running")
        
        # Check if workers are still alive
        dead_workers = [i for i, w in enumerate(self.workers) if not w.is_alive()]
        if dead_workers:
            logger.error(f"Workers {dead_workers} are dead. Pool may be unstable.")
            # Don't fail immediately - try to continue with remaining workers
            if len(dead_workers) == len(self.workers):
                raise RuntimeError("All browser workers are dead. Pool is unusable.")
        
        # Generate unique command ID
        command_id = str(uuid.uuid4())
        # Use longer timeout for slow operations like fill_form
        default_timeout = getattr(settings, 'BROWSER_WORKER_TIMEOUT', 60)
        if command_type == "fill_form":
            # Fill form can take longer, especially with select dropdowns
            timeout = timeout or max(default_timeout, 120)  # At least 120 seconds for fill_form
        else:
            timeout = timeout or default_timeout
        
        # Create command
        command = BrowserCommand(
            command_id=command_id,
            command_type=command_type,
            params=params
        )
        
        # Get worker to use (round-robin)
        worker_index = self._get_next_worker()
        command_queue = self.command_queues[worker_index]
        result_queue = self.result_queues[worker_index]
        
        # Send command
        try:
            command_queue.put(command.to_dict(), timeout=5.0)
        except Exception as e:
            raise RuntimeError(f"Failed to send command to worker {worker_index}: {e}")
        
        # Wait for result with timeout
        try:
            # Poll result queue with timeout
            # Use a loop to periodically check the queue (multiprocessing.Queue doesn't work well with asyncio)
            import time
            start_time = time.time()
            unmatched_results = []  # Store results that don't match our command ID
            
            while True:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    # Put back any unmatched results
                    for unmatched in unmatched_results:
                        try:
                            result_queue.put(unmatched, block=False)
                        except:
                            pass
                    raise TimeoutError(f"Command {command_type} timed out after {timeout}s")
                
                # Check if result is available (non-blocking)
                if not result_queue.empty():
                    try:
                        result_dict = result_queue.get_nowait()
                        result = BrowserResult.from_dict(result_dict)
                        
                        # Verify command ID matches
                        if result.command_id == command_id:
                            # Put back any unmatched results we collected
                            for unmatched in unmatched_results:
                                try:
                                    result_queue.put(unmatched, block=False)
                                except:
                                    pass
                            return result
                        else:
                            # Wrong command ID - check if it matches any pending command
                            # For now, store it and continue (with round-robin, this shouldn't happen often)
                            unmatched_results.append(result_dict)
                            logger.debug(
                                f"Received result for different command ID: "
                                f"expected {command_id}, got {result.command_id}. "
                                f"Storing (have {len(unmatched_results)} unmatched)."
                            )
                    except Exception as e:
                        logger.debug(f"Error getting result from queue: {e}")
                
                # Also check unmatched results periodically (in case we stored our result earlier)
                for i, unmatched_dict in enumerate(unmatched_results):
                    unmatched_result = BrowserResult.from_dict(unmatched_dict)
                    if unmatched_result.command_id == command_id:
                        # Found our result! Remove it and return
                        unmatched_results.pop(i)
                        # Put back remaining unmatched results
                        for remaining in unmatched_results:
                            try:
                                result_queue.put(remaining, block=False)
                            except:
                                pass
                        return unmatched_result
                
                # Wait a bit before checking again (non-blocking sleep)
                await asyncio.sleep(0.1)
        
        except TimeoutError:
            logger.error(f"Command {command_type} (ID: {command_id}) timed out")
            return BrowserResult.error_result(
                command_id,
                f"Command timed out after {timeout}s",
                "TimeoutError"
            )
        except Exception as e:
            logger.error(f"Error waiting for result: {e}")
            return BrowserResult.error_result(
                command_id,
                str(e),
                type(e).__name__
            )
    
    def is_available(self) -> bool:
        """
        Check if the worker pool is available and running.
        
        Returns:
            True if pool is running and ready, False otherwise
        """
        if not self.use_pool:
            return False
        return self.is_running and len(self.workers) > 0 and all(w.is_alive() for w in self.workers)


# Global pool instance
_browser_pool: Optional[BrowserWorkerPool] = None


def get_browser_pool() -> BrowserWorkerPool:
    """
    Get or create the global browser worker pool instance.
    
    Returns:
        BrowserWorkerPool instance
    """
    global _browser_pool
    if _browser_pool is None:
        _browser_pool = BrowserWorkerPool()
    return _browser_pool


def start_browser_pool():
    """Start the global browser worker pool"""
    pool = get_browser_pool()
    pool.start()


def stop_browser_pool():
    """Stop the global browser worker pool"""
    global _browser_pool
    if _browser_pool:
        _browser_pool.stop()
        _browser_pool = None
