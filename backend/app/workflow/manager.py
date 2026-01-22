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
    Manages the submission queue and processes submissions in batches
    """
    
    def __init__(
        self,
        max_concurrent: Optional[int] = None,
        batch_size: Optional[int] = None,
        processing_interval: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        self.max_concurrent = max_concurrent or settings.WORKFLOW_MAX_CONCURRENT
        self.batch_size = batch_size or settings.WORKFLOW_BATCH_SIZE
        self.processing_interval = processing_interval or settings.WORKFLOW_PROCESSING_INTERVAL
        self.max_retries = max_retries or settings.WORKFLOW_MAX_RETRIES
        
        self.is_running = False
        self.processing_tasks: Dict[int, asyncio.Task] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        self.lock = threading.Lock()
        
        logger.info(
            f"WorkflowManager initialized: "
            f"max_concurrent={max_concurrent}, "
            f"batch_size={batch_size}, "
            f"interval={processing_interval}s"
        )
    
    async def start(self):
        """
        Start the workflow manager
        Begins periodic processing of pending submissions
        """
        if self.is_running:
            logger.warning("WorkflowManager is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("WorkflowManager started")
    
    async def stop(self):
        """
        Stop the workflow manager
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
        Process a batch of pending submissions
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
        Process a single submission
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
            
            # Update status to "submitted" (processing)
            update_submission(db, submission_id, SubmissionUpdate(status="submitted"))
            
            # Process submission
            workflow = SubmissionWorkflow()
            
            # Create screenshot path for this submission
            screenshot_dir = "./storage/screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"submission_{submission_id}_{int(time.time())}.png")
            
            result = await workflow.submit_to_directory(
                directory_url=directory.url,
                saas_data=saas_data,
                screenshot_path=screenshot_path
            )
            
            # Store form structure and HTML for debugging
            form_structure = result.get("form_structure", {})
            form_data_dict = {
                "form_structure": form_structure,
                "fields_filled": result.get("fields_filled", 0),
                "total_fields": result.get("total_fields", 0),
                "fill_errors": result.get("fill_errors", []),
                "screenshot_path": screenshot_path if os.path.exists(screenshot_path) else None
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
            elif result.get("status") == "error":
                # Retry if under max retries
                if submission.retry_count < self.max_retries - 1:
                    update_data["status"] = "pending"
                    update_data["retry_count"] = submission.retry_count + 1
                    update_data["error_message"] = f"Retry {update_data['retry_count']}/{self.max_retries}: {result.get('message', 'Unknown error')}"
                    logger.info(f"Submission {submission_id} will be retried: {update_data['error_message']}")
                else:
                    update_data["status"] = "failed"
                    update_data["error_message"] = result.get("message", "Unknown error")
                    logger.error(f"Submission {submission_id} failed after {submission.retry_count + 1} attempts")
            elif result.get("status") == "captcha_required":
                # CAPTCHA requires manual intervention, mark as failed
                update_data["status"] = "failed"
                update_data["error_message"] = "CAPTCHA detected - manual intervention required"
                logger.warning(f"Submission {submission_id} requires CAPTCHA")
            else:
                # Unknown status, mark as failed
                update_data["status"] = "failed"
                update_data["error_message"] = f"Unknown status: {result.get('status')}"
                logger.warning(f"Submission {submission_id} returned unknown status: {result.get('status')}")
            
            update_submission(db, submission_id, SubmissionUpdate(**update_data))
        
        except Exception as e:
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
        Get current status of the workflow manager
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
