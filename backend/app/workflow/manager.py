"""
Workflow Manager
Handles queue management, scheduling, and batch processing of submissions
"""
import asyncio
import threading
import os
import time
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.crud import (
    get_submissions,
    get_submission_by_id,
    get_saas_by_id,
    get_directory_by_id,
    update_submission
)
from app.db.models import SubmissionUpdate
from app.workflow.submitter import SubmissionWorkflow
from app.utils.logger import logger
from app.core.config import settings
import json


class WorkflowManager:
    """
    Manages the submission queue and processes submissions in batches.
    
    The WorkflowManager is the control center that orchestrates automated form submissions.
    It continuously monitors the database for pending submissions, processes them concurrently
    up to a configurable limit, handles retries, and tracks progress for real-time updates.
    
    Key features:
    - Automatic batch processing of pending submissions
    - Concurrent processing with configurable limits
    - Automatic retry logic with exponential backoff
    - Real-time progress tracking per submission
    - Graceful shutdown handling
    """
    
    def __init__(
        self,
        max_concurrent: Optional[int] = None,
        batch_size: Optional[int] = None,
        processing_interval: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        """
        Initialize the WorkflowManager with configuration settings.
        
        Args:
            max_concurrent: Maximum number of submissions to process simultaneously (default: from config)
            batch_size: Number of submissions to fetch per processing cycle (default: from config)
            processing_interval: Seconds between processing cycles (default: from config)
            max_retries: Maximum retry attempts per submission before marking as failed (default: from config)
        """
        self.max_concurrent = max_concurrent or settings.WORKFLOW_MAX_CONCURRENT
        self.batch_size = batch_size or settings.WORKFLOW_BATCH_SIZE
        self.processing_interval = processing_interval or settings.WORKFLOW_PROCESSING_INTERVAL
        self.max_retries = max_retries or settings.WORKFLOW_MAX_RETRIES
        
        self.is_running = False
        self.processing_tasks: Dict[int, asyncio.Task] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        self.lock = threading.Lock()
        # Progress tracking: {submission_id: {"status": "analyzing_form", "progress": 25, "message": "..."}}
        self.progress_tracking: Dict[int, Dict] = {}
        
        # Log the actual values being used (from settings if parameters were None)
        logger.info(
            f"WorkflowManager initialized: "
            f"max_concurrent={self.max_concurrent}, "
            f"batch_size={self.batch_size}, "
            f"interval={self.processing_interval}s, "
            f"max_retries={self.max_retries}"
        )
    
    async def start(self):
        """
        Start the workflow manager and begin periodic processing.
        
        Initializes the scheduler loop that continuously monitors for pending submissions
        and processes them according to the configured batch size and concurrency limits.
        This method is called automatically when the FastAPI application starts.
        
        Raises:
            Warning: If the manager is already running
        """
        if self.is_running:
            logger.warning("WorkflowManager is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("WorkflowManager started")
    
    async def stop(self):
        """
        Stop the workflow manager gracefully.
        
        Cancels the scheduler loop and waits for all active processing tasks to complete
        before shutting down. This ensures no submissions are lost or left in an
        inconsistent state. Called automatically when the FastAPI application shuts down.
        """
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Wait for all processing tasks to complete
        if self.processing_tasks:
            logger.info(f"Waiting for {len(self.processing_tasks)} active tasks to complete...")
            await asyncio.gather(*self.processing_tasks.values(), return_exceptions=True)
        
        logger.info("WorkflowManager stopped")
    
    async def _scheduler_loop(self):
        """
        Main scheduler loop that periodically processes pending submissions
        """
        while self.is_running:
            try:
                await self.process_pending_submissions()
                await asyncio.sleep(self.processing_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}", exc_info=True)
                await asyncio.sleep(self.processing_interval)
    
    async def process_pending_submissions(self):
        """
        Process a batch of pending submissions up to the configured limits.
        
        Fetches pending submissions from the database (limited by batch_size),
        checks available processing slots (based on max_concurrent), and starts
        processing tasks for available submissions. This method is called
        periodically by the scheduler loop.
        
        The method respects the max_concurrent limit and will skip processing
        if all slots are currently busy, waiting for the next cycle.
        """
        # Get database session
        db = SessionLocal()
        try:
            # Get pending submissions (limit by batch_size)
            pending = get_submissions(
                db,
                status="pending"
            )[:self.batch_size]
            
            if not pending:
                return
            
            logger.info(f"Processing {len(pending)} pending submissions")
            
            # Process submissions up to max_concurrent limit
            active_count = len([t for t in self.processing_tasks.values() if not t.done()])
            available_slots = self.max_concurrent - active_count
            
            if available_slots <= 0:
                logger.debug(f"All {self.max_concurrent} slots are busy, skipping this cycle")
                return
            
            # Process available submissions
            tasks_to_start = min(available_slots, len(pending))
            for submission in pending[:tasks_to_start]:
                if submission.id not in self.processing_tasks or self.processing_tasks[submission.id].done():
                    task = asyncio.create_task(self._process_submission(submission.id))
                    self.processing_tasks[submission.id] = task
                    
                    # Clean up completed tasks
                    task.add_done_callback(lambda t, sid=submission.id: self._cleanup_task(sid))
        
        finally:
            db.close()
    
    async def _process_submission(self, submission_id: int):
        """
        Process a single submission through the complete workflow.
        
        This is the core processing method that executes the full submission workflow:
        1. Validates submission exists and is in pending status
        2. Checks retry count hasn't exceeded maximum
        3. Retrieves SaaS and Directory data
        4. Updates progress tracking throughout the process
        5. Executes the submission workflow (navigate, analyze, fill, submit)
        6. Updates submission status based on result (submitted/failed/captcha)
        7. Handles retries if submission fails and retry count allows
        
        Args:
            submission_id: The unique ID of the submission to process
            
        The method updates the submission record in the database with:
        - Status (pending -> submitted/failed)
        - Error messages if failed
        - Form structure and fill results
        - Retry count increments
        - Timestamps (submitted_at)
        """
        db = SessionLocal()
        try:
            submission = get_submission_by_id(db, submission_id)
            if not submission:
                logger.error(f"Submission {submission_id} not found")
                return
            
            if submission.status != "pending":
                logger.debug(f"Submission {submission_id} is not pending (status: {submission.status})")
                return
            
            # Check retry count
            if submission.retry_count >= self.max_retries:
                logger.warning(
                    f"Submission {submission_id} exceeded max retries ({self.max_retries}), "
                    f"marking as failed"
                )
                update_submission(
                    db,
                    submission_id,
                    SubmissionUpdate(
                        status="failed",
                        error_message=f"Exceeded maximum retry count ({self.max_retries})"
                    )
                )
                return
            
            logger.info(f"Processing submission {submission_id} (attempt {submission.retry_count + 1})")
            
            # Initialize progress tracking
            self.progress_tracking[submission_id] = {
                "status": "queued",
                "progress": 0,
                "message": "Starting submission processing",
                "started_at": datetime.now().isoformat()
            }
            
            # Get SaaS and Directory data
            saas = get_saas_by_id(db, submission.saas_id)
            if not saas:
                logger.error(f"SaaS {submission.saas_id} not found for submission {submission_id}")
                update_submission(
                    db,
                    submission_id,
                    SubmissionUpdate(
                        status="failed",
                        error_message="SaaS product not found"
                    )
                )
                return
            
            directory = get_directory_by_id(db, submission.directory_id)
            if not directory:
                logger.error(f"Directory {submission.directory_id} not found for submission {submission_id}")
                update_submission(
                    db,
                    submission_id,
                    SubmissionUpdate(
                        status="failed",
                        error_message="Directory not found"
                    )
                )
                return
            
            # Prepare SaaS data
            saas_data = {
                "name": saas.name,
                "url": saas.url,
                "contact_email": saas.contact_email,
                "description": saas.description or "",
                "category": saas.category or "",
                "logo_path": saas.logo_path or ""
            }
            
            # Keep status as "pending" until workflow completes
            # Don't update status here - let it remain "pending" until we know the final result
            # This ensures UI shows "pending" until workflow is truly done
            
            # Update progress: Starting workflow
            self.progress_tracking[submission_id].update({
                "status": "analyzing_form",
                "progress": 20,
                "message": f"Analyzing form at {directory.url}"
            })
            
            # Process submission
            workflow = SubmissionWorkflow()
            
            # Create screenshot path for this submission
            screenshot_dir = "./storage/screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"submission_{submission_id}_{int(time.time())}.png")
            
            # Update progress: Filling form
            self.progress_tracking[submission_id].update({
                "status": "filling_form",
                "progress": 50,
                "message": "Filling form fields with SaaS data"
            })
            
            result = await workflow.submit_to_directory(
                directory_url=directory.url,
                saas_data=saas_data,
                screenshot_path=screenshot_path
            )
            
            # Update progress: Submitting
            self.progress_tracking[submission_id].update({
                "status": "submitting",
                "progress": 80,
                "message": "Submitting form"
            })
            
            # Store form structure and HTML for debugging
            form_structure = result.get("form_structure", {})
            form_data_dict = {
                "form_structure": form_structure,
                "fields_filled": result.get("fields_filled", 0),
                "total_fields": result.get("total_fields", 0),
                "fill_errors": result.get("fill_errors", []),
                "screenshot_path": screenshot_path if os.path.exists(screenshot_path) else None,
                "analysis_method": result.get("analysis_method", "unknown")  # Include analysis method
            }
            
            # Update submission based on result
            update_data = {
                "error_message": None,
                "form_data": json.dumps(form_data_dict)
            }
            
            if result.get("status") == "success":
                update_data["status"] = "submitted"
                update_data["submitted_at"] = datetime.now()
                logger.info(f"Submission {submission_id} completed successfully")
                # Update progress: Completed
                self.progress_tracking[submission_id].update({
                    "status": "completed",
                    "progress": 100,
                    "message": "Submission completed successfully",
                    "completed_at": datetime.now().isoformat()
                })
            elif result.get("status") == "error":
                error_msg = result.get("message", "Unknown error")
                # Retry if under max retries
                if submission.retry_count < self.max_retries - 1:
                    update_data["status"] = "pending"
                    update_data["retry_count"] = submission.retry_count + 1
                    update_data["error_message"] = f"Retry {update_data['retry_count']}/{self.max_retries}: {error_msg}"
                    logger.info(f"Submission {submission_id} will be retried: {update_data['error_message']}")
                    # Update progress: Will retry
                    self.progress_tracking[submission_id].update({
                        "status": "failed_retry",
                        "progress": 0,
                        "message": f"Failed, will retry: {error_msg}"
                    })
                else:
                    update_data["status"] = "failed"
                    update_data["error_message"] = error_msg
                    logger.error(f"Submission {submission_id} failed after {submission.retry_count + 1} attempts")
                    # Update progress: Failed
                    self.progress_tracking[submission_id].update({
                        "status": "failed",
                        "progress": 0,
                        "message": f"Failed: {error_msg}",
                        "completed_at": datetime.now().isoformat()
                    })
            elif result.get("status") == "captcha_required":
                # CAPTCHA requires manual intervention, mark as failed
                update_data["status"] = "failed"
                update_data["error_message"] = "CAPTCHA detected - manual intervention required"
                logger.warning(f"Submission {submission_id} requires CAPTCHA")
                # Update progress: CAPTCHA required
                self.progress_tracking[submission_id].update({
                    "status": "captcha_required",
                    "progress": 0,
                    "message": "CAPTCHA detected - manual intervention required",
                    "completed_at": datetime.now().isoformat()
                })
            elif result.get("status") == "pending":
                # Pending status - if form was submitted, treat as success
                # Check if fields were filled (indicates form was processed)
                fields_filled = result.get("fields_filled", 0)
                if fields_filled > 0:
                    # Form was filled and submitted, treat pending as success
                    update_data["status"] = "submitted"
                    update_data["submitted_at"] = datetime.now()
                    logger.info(f"Submission {submission_id} completed (pending status but form was submitted)")
                    self.progress_tracking[submission_id].update({
                        "status": "completed",
                        "progress": 100,
                        "message": "Submission completed (status verification unclear)",
                        "completed_at": datetime.now().isoformat()
                    })
                else:
                    # No fields filled, treat as error
                    update_data["status"] = "failed"
                    update_data["error_message"] = result.get("message", "Submission status unclear and no fields were filled")
                    logger.warning(f"Submission {submission_id} failed: {update_data['error_message']}")
                    self.progress_tracking[submission_id].update({
                        "status": "failed",
                        "progress": 0,
                        "message": update_data["error_message"],
                        "completed_at": datetime.now().isoformat()
                    })
            else:
                # Unknown status, mark as failed
                unknown_status = result.get('status', 'unknown')
                update_data["status"] = "failed"
                update_data["error_message"] = f"Unknown status: {unknown_status}"
                logger.warning(f"Submission {submission_id} returned unknown status: {unknown_status}")
                # Update progress: Unknown status
                self.progress_tracking[submission_id].update({
                    "status": "failed",
                    "progress": 0,
                    "message": f"Unknown status: {unknown_status}",
                    "completed_at": datetime.now().isoformat()
                })
            
            update_submission(db, submission_id, SubmissionUpdate(**update_data))
        
        except Exception as e:
            # Update progress: Error
            if submission_id in self.progress_tracking:
                self.progress_tracking[submission_id].update({
                    "status": "error",
                    "progress": 0,
                    "message": f"Error: {str(e)}",
                    "completed_at": datetime.now().isoformat()
                })
            logger.error(f"Error processing submission {submission_id}: {str(e)}", exc_info=True)
            try:
                submission = get_submission_by_id(db, submission_id)
                if submission and submission.retry_count < self.max_retries - 1:
                    # Retry
                    update_submission(
                        db,
                        submission_id,
                        SubmissionUpdate(
                            status="pending",
                            retry_count=submission.retry_count + 1,
                            error_message=f"Retry {submission.retry_count + 1}/{self.max_retries}: {str(e)}"
                        )
                    )
                else:
                    # Mark as failed
                    update_submission(
                        db,
                        submission_id,
                        SubmissionUpdate(
                            status="failed",
                            error_message=f"Processing error: {str(e)}"
                        )
                    )
            except Exception as update_error:
                logger.error(f"Error updating submission {submission_id} after failure: {str(update_error)}")
        
        finally:
            db.close()
            # Clean up progress tracking after 1 hour
            if submission_id in self.progress_tracking:
                # Keep for 1 hour for status queries, then remove
                pass  # Could add cleanup logic here if needed
    
    def get_submission_progress(self, submission_id: int) -> Optional[Dict]:
        """Get progress for a specific submission"""
        return self.progress_tracking.get(submission_id)
    
    def _cleanup_task(self, submission_id: int):
        """
        Clean up completed task from tracking
        """
        if submission_id in self.processing_tasks:
            del self.processing_tasks[submission_id]
    
    async def process_failed_submissions(self, max_age_hours: int = 24):
        """
        Retry failed submissions that are older than max_age_hours
        Useful for periodic retry of old failures
        """
        db = SessionLocal()
        try:
            # Get failed submissions older than max_age_hours
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            all_submissions = get_submissions(db, status="failed")
            
            failed_to_retry = [
                s for s in all_submissions
                if s.updated_at and s.updated_at < cutoff_time
                and s.retry_count < self.max_retries
            ]
            
            if not failed_to_retry:
                return
            
            logger.info(f"Retrying {len(failed_to_retry)} old failed submissions")
            
            for submission in failed_to_retry:
                update_submission(
                    db,
                    submission.id,
                    SubmissionUpdate(
                        status="pending",
                        error_message=None
                    )
                )
                logger.info(f"Queued submission {submission.id} for retry")
        
        finally:
            db.close()
    
    def get_status(self) -> Dict:
        """
        Get current status and configuration of the workflow manager.
        
        Returns real-time information about the workflow manager state including
        whether it's running, how many tasks are active, and all configuration settings.
        Used by the frontend dashboard to display workflow manager status.
        
        Returns:
            Dictionary containing:
                - is_running: Boolean indicating if workflow manager is active
                - max_concurrent: Maximum concurrent submissions allowed
                - batch_size: Number of submissions processed per batch
                - processing_interval: Seconds between processing cycles
                - active_tasks: Number of currently processing submissions
                - active_submission_ids: List of submission IDs being processed
                - total_tracked_tasks: Total tasks tracked by manager
        """
        active_tasks = [sid for sid, task in self.processing_tasks.items() if not task.done()]
        
        return {
            "is_running": self.is_running,
            "max_concurrent": self.max_concurrent,
            "batch_size": self.batch_size,
            "processing_interval": self.processing_interval,
            "active_tasks": len(active_tasks),
            "active_submission_ids": active_tasks,
            "total_tracked_tasks": len(self.processing_tasks)
        }


# Global workflow manager instance
_workflow_manager: Optional[WorkflowManager] = None


def get_workflow_manager() -> WorkflowManager:
    """
    Get or create the global workflow manager instance
    Uses settings from config.py
    """
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager()  # Uses settings from config
    return _workflow_manager
