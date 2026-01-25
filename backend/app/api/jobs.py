"""
Job/workflow API routes for managing submission jobs
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import asyncio
from app.utils.rate_limit import limiter, get_rate_limit
from app.db.crud import (
    get_saas_by_id,
    get_directory_by_id,
    get_directories,
    get_submission_by_saas_directory,
    get_submission_by_id,
    create_submission,
    get_submissions,
    update_submission,
)
from app.db.models import Submission, SubmissionCreate, SubmissionUpdate
from app.db.session import get_db, SessionLocal
from app.core.security import get_current_user
from app.workflow.submitter import SubmissionWorkflow
from app.workflow.manager import get_workflow_manager
from app.utils.logger import logger
from datetime import datetime
import json

router = APIRouter()


class StartJobRequest(BaseModel):
    saas_id: int
    directory_ids: Optional[List[int]] = None  # If None, submit to all directories


class JobResponse(BaseModel):
    job_id: str
    message: str
    saas_id: int
    total_directories: int
    submissions_created: int
    status: str


@router.post("/start", response_model=JobResponse)
@limiter.limit(get_rate_limit("jobs"))
async def start_submission_job(
    request: Request,
    job_request: StartJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Start a submission job for a SaaS product across multiple directories.
    
    Creates submission records for the specified SaaS product and directories,
    then queues them for processing by the workflow manager. If no directories
    are specified, submits to all available directories. Skips directories where
    a submission already exists.
    
    Args:
        job_request: StartJobRequest containing:
            - saas_id: ID of the SaaS product to submit
            - directory_ids: Optional list of directory IDs (None = all directories)
        background_tasks: FastAPI background tasks for async processing
        db: Database session dependency
        
    Returns:
        JobResponse with job details including:
            - job_id: Unique job identifier
            - message: Status message
            - saas_id: SaaS product ID
            - total_directories: Total directories in job
            - submissions_created: Number of new submission records created
            - status: Job status ("queued")
            
    Raises:
        HTTPException: 404 if SaaS product not found
        HTTPException: 400 if directory IDs are invalid or no directories available
    """
    # Verify SaaS exists
    saas = get_saas_by_id(db, job_request.saas_id)
    if not saas:
        raise HTTPException(status_code=404, detail="SaaS product not found")

    # Get directories to submit to
    if job_request.directory_ids:
        directories = [
            d for d in get_directories(db) if d.id in job_request.directory_ids
        ]
        if len(directories) != len(job_request.directory_ids):
            raise HTTPException(
                status_code=400, detail="One or more directory IDs not found"
            )
    else:
        # Submit to all directories
        directories = get_directories(db)

    if not directories:
        raise HTTPException(
            status_code=400, detail="No directories available for submission"
        )

    # Create submission records (skip if already exists)
    submissions_created = 0
    job_id = f"job_{saas.id}_{int(datetime.now().timestamp())}"

    for directory in directories:
        # Check if submission already exists
        existing = get_submission_by_saas_directory(
            db, job_request.saas_id, directory.id
        )

        if existing:
            logger.info(
                f"Submission already exists for SaaS {job_request.saas_id} "
                f"and directory {directory.id}, skipping"
            )
            continue

        # Create new submission record
        submission_data = SubmissionCreate(
            saas_id=job_request.saas_id, directory_id=directory.id, status="pending"
        )
        create_submission(db, submission_data)
        submissions_created += 1

    # TODO: Queue job for background processing
    # For now, we just create the submission records
    # The actual workflow processing will be handled by the workflow manager

    logger.info(
        f"Job {job_id} started: {submissions_created} submissions created "
        f"for SaaS {job_request.saas_id}"
    )

    return JobResponse(
        job_id=job_id,
        message=f"Submission job started. {submissions_created} submissions queued.",
        saas_id=job_request.saas_id,
        total_directories=len(directories),
        submissions_created=submissions_created,
        status="queued",
    )


@router.get("/status/{saas_id}")
async def get_job_status(
    saas_id: int,
    db: Session = Depends(get_db),
):
    """
    Get submission job status for a SaaS product.
    
    Retrieves all submissions for a specific SaaS product and provides
    a summary breakdown by status (pending, submitted, approved, failed).
    
    Args:
        saas_id: ID of the SaaS product to get status for
        db: Database session dependency
        
    Returns:
        Dictionary containing:
            - saas_id: SaaS product ID
            - saas_name: Name of the SaaS product
            - total_submissions: Total number of submissions
            - status_breakdown: Dictionary with counts by status
            - submissions: List of all submission objects
            
    Raises:
        HTTPException: 404 if SaaS product not found
    """
    # Verify SaaS exists
    saas = get_saas_by_id(db, saas_id)
    if not saas:
        raise HTTPException(status_code=404, detail="SaaS product not found")

    submissions = get_submissions(db, saas_id=saas_id)

    status_counts = {"pending": 0, "submitted": 0, "approved": 0, "failed": 0}

    for submission in submissions:
        status_counts[submission.status] = status_counts.get(submission.status, 0) + 1

    return {
        "saas_id": saas_id,
        "saas_name": saas.name,
        "total_submissions": len(submissions),
        "status_breakdown": status_counts,
        "submissions": submissions,
    }


@router.post("/process/{submission_id}")
async def process_submission(
    submission_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Process a single submission by executing the complete workflow.
    
    Manually triggers the submission workflow for a specific submission.
    The workflow includes:
    1. Navigate to the directory submission page
    2. Detect and analyze the form structure (using AI or DOM extraction)
    3. Map SaaS data to form fields
    4. Fill form fields with SaaS information
    5. Submit the form
    6. Verify submission and update status in database
    
    Args:
        submission_id: ID of the submission to process
        background_tasks: FastAPI background tasks for async processing
        db: Database session dependency
        
    Returns:
        Dictionary with:
            - message: Status message
            - submission_id: ID of the submission
            - status: Processing status ("processing")
            
    Raises:
        HTTPException: 404 if submission, SaaS, or directory not found
        HTTPException: 400 if submission status is not "pending" or "failed"
    """
    # Get submission
    submission = get_submission_by_id(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.status not in ["pending", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot process submission with status: {submission.status}",
        )

    # Get SaaS and Directory data
    saas = get_saas_by_id(db, submission.saas_id)
    if not saas:
        raise HTTPException(status_code=404, detail="SaaS product not found")

    directory = get_directory_by_id(db, submission.directory_id)
    if not directory:
        raise HTTPException(status_code=404, detail="Directory not found")

    # Prepare SaaS data for submission
    saas_data = {
        "name": saas.name,
        "url": saas.url,
        "contact_email": saas.contact_email,
        "description": saas.description or "",
        "category": saas.category or "",
        "logo_path": saas.logo_path or "",
    }

    # Update status to "submitted" (processing)
    update_submission(db, submission_id, SubmissionUpdate(status="submitted"))

    # Process in background
    async def process_workflow():
        try:
            workflow = SubmissionWorkflow()
            result = await workflow.submit_to_directory(
                directory_url=directory.url, saas_data=saas_data
            )

            # Update submission based on result
            update_data = {
                "status": result.get("status", "failed"),
                "error_message": None,
                "form_data": json.dumps(result.get("form_structure", {})),
            }

            if result.get("status") == "success":
                update_data["status"] = "submitted"
                update_data["submitted_at"] = datetime.now()
            elif result.get("status") == "error":
                update_data["status"] = "failed"
                update_data["error_message"] = result.get("message", "Unknown error")
            elif result.get("status") == "captcha_required":
                update_data["status"] = "failed"
                update_data["error_message"] = (
                    "CAPTCHA detected - manual intervention required"
                )

            update_submission(db, submission_id, SubmissionUpdate(**update_data))
            logger.info(
                f"Submission {submission_id} processed with status: {result.get('status')}"
            )

        except Exception as e:
            logger.error(f"Error processing submission {submission_id}: {str(e)}")
            update_submission(
                db,
                submission_id,
                SubmissionUpdate(
                    status="failed", error_message=f"Processing error: {str(e)}"
                ),
            )

    background_tasks.add_task(process_workflow)

    return {
        "message": "Submission queued for processing",
        "submission_id": submission_id,
        "status": "processing",
    }


@router.get("/workflow/status")
@limiter.limit(get_rate_limit("stats"))
async def get_workflow_status(request: Request):
    """
    Get the current status of the workflow manager with detailed active submission information.
    
    Returns real-time information about the workflow manager including
    progress details for each active submission.
    
    Returns:
        Dictionary containing:
            - is_running: Boolean indicating if workflow manager is active
            - max_concurrent: Maximum concurrent submissions allowed
            - batch_size: Number of submissions processed per batch
            - processing_interval: Seconds between processing cycles
            - active_tasks: Number of currently processing submissions
            - active_submission_ids: List of submission IDs being processed
            - total_tracked_tasks: Total tasks tracked by manager
            - active_submissions: List of active submission details with progress
            - queue_length: Number of pending submissions waiting to be processed
    """
    from app.db.session import SessionLocal
    from app.db.crud import get_submissions, get_submission_by_id
    
    manager = get_workflow_manager()
    status = manager.get_status()
    
    # Get detailed information about active submissions
    active_submission_ids = status.get("active_submission_ids", [])
    active_submissions = []
    
    db = SessionLocal()
    try:
        for submission_id in active_submission_ids:
            submission = get_submission_by_id(db, submission_id)
            if submission:
                progress = manager.get_submission_progress(submission_id) or {}
                active_submissions.append({
                    "submission_id": submission_id,
                    "saas_id": submission.saas_id,
                    "directory_id": submission.directory_id,
                    "status": progress.get("status", "processing"),
                    "progress": progress.get("progress", 0),
                    "message": progress.get("message", "Processing..."),
                    "started_at": progress.get("started_at"),
                    "retry_count": submission.retry_count
                })
    finally:
        db.close()
    
    # Get queue length (pending submissions not yet processing)
    db = SessionLocal()
    try:
        pending_submissions = get_submissions(db, status="pending")
        queue_length = len([s for s in pending_submissions if s.id not in active_submission_ids])
    finally:
        db.close()
    
    status["active_submissions"] = active_submissions
    status["queue_length"] = queue_length
    
    return status


@router.post("/workflow/process-pending")
@limiter.limit(get_rate_limit("jobs"))
async def trigger_processing(request: Request):
    """
    Manually trigger processing of pending submissions
    """
    manager = get_workflow_manager()
    await manager.process_pending_submissions()
    return {"message": "Processing triggered", "status": manager.get_status()}


@router.post("/workflow/retry-failed")
async def retry_failed_submissions(max_age_hours: int = 24):
    """
    Retry failed submissions older than max_age_hours
    """
    manager = get_workflow_manager()
    await manager.process_failed_submissions(max_age_hours=max_age_hours)
    return {
        "message": f"Retry process triggered for submissions older than {max_age_hours} hours"
    }


@router.post("/process-all")
@limiter.limit(get_rate_limit("jobs"))
async def process_all_pending(
    request: Request,
    limit: Optional[int] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Process all pending submissions immediately
    """
    pending = get_submissions(db, status="pending")
    if limit:
        pending = pending[:limit]

    if not pending:
        return {
            "message": "No pending submissions found",
            "count": 0,
            "submission_ids": []
        }

    submission_ids = [s.id for s in pending]

    # Process in background
    async def process_all():
        manager = get_workflow_manager()
        for submission_id in submission_ids:
            if submission_id not in manager.processing_tasks or manager.processing_tasks[submission_id].done():
                task = asyncio.create_task(manager._process_submission(submission_id))
                manager.processing_tasks[submission_id] = task
                task.add_done_callback(lambda t, sid=submission_id: manager._cleanup_task(sid))
                # Small delay between starting tasks
                await asyncio.sleep(0.5)

    if background_tasks:
        background_tasks.add_task(process_all)
        return {
            "message": f"Processing {len(pending)} pending submissions in background",
            "count": len(pending),
            "submission_ids": submission_ids
        }
    else:
        await process_all()
        return {
            "message": f"Processed {len(pending)} pending submissions",
            "count": len(pending),
            "submission_ids": submission_ids
        }


@router.post("/process-saas/{saas_id}")
async def process_saas_submissions(
    saas_id: int,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Process all pending submissions for a specific SaaS product
    """
    saas = get_saas_by_id(db, saas_id)
    if not saas:
        raise HTTPException(status_code=404, detail="SaaS product not found")

    submissions = get_submissions(db, saas_id=saas_id, status="pending")
    if not submissions:
        return {
            "message": f"No pending submissions found for SaaS: {saas.name}",
            "count": 0,
            "submission_ids": []
        }

    submission_ids = [s.id for s in submissions]

    # Process in background
    async def process_saas():
        manager = get_workflow_manager()
        for submission_id in submission_ids:
            if submission_id not in manager.processing_tasks or manager.processing_tasks[submission_id].done():
                task = asyncio.create_task(manager._process_submission(submission_id))
                manager.processing_tasks[submission_id] = task
                task.add_done_callback(lambda t, sid=submission_id: manager._cleanup_task(sid))
                await asyncio.sleep(0.5)

    if background_tasks:
        background_tasks.add_task(process_saas)
        return {
            "message": f"Processing {len(submissions)} submissions for SaaS: {saas.name}",
            "saas_id": saas_id,
            "saas_name": saas.name,
            "count": len(submissions),
            "submission_ids": submission_ids
        }
    else:
        await process_saas()
        return {
            "message": f"Processed {len(submissions)} submissions for SaaS: {saas.name}",
            "saas_id": saas_id,
            "saas_name": saas.name,
            "count": len(submissions),
            "submission_ids": submission_ids
        }


@router.get("/progress/{submission_id}")
@limiter.limit(get_rate_limit("stats"))
async def get_submission_progress(request: Request, submission_id: int):
    """
    Get real-time progress for a specific submission.
    
    Returns detailed progress information for a submission that is currently
    being processed, including current step, progress percentage, and status message.
    If the submission is not currently being processed, returns basic status.
    
    Args:
        submission_id: ID of the submission to get progress for
        
    Returns:
        Dictionary containing:
            - submission_id: ID of the submission
            - status: Current processing status (queued, analyzing_form, filling_form, etc.)
            - progress: Progress percentage (0-100)
            - message: Current status message
            - started_at: ISO timestamp when processing started
            - completed_at: ISO timestamp when processing completed (if finished)
            
    Raises:
        HTTPException: 404 if submission not found
    """
    manager = get_workflow_manager()
    progress = manager.get_submission_progress(submission_id)
    
    if not progress:
        # Check if submission exists and get basic status
        db = SessionLocal()
        try:
            submission = get_submission_by_id(db, submission_id)
            if not submission:
                raise HTTPException(status_code=404, detail="Submission not found")
            
            return {
                "submission_id": submission_id,
                "status": submission.status,
                "progress": None,
                "message": f"Status: {submission.status}"
            }
        finally:
            db.close()
    
    return {
        "submission_id": submission_id,
        **progress
    }


@router.post("/batch-process")
async def batch_process_submissions(
    submission_ids: List[int],
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Process multiple submissions by their IDs
    """
    if not submission_ids:
        raise HTTPException(status_code=400, detail="No submission IDs provided")

    # Verify all submissions exist
    valid_ids = []
    for submission_id in submission_ids:
        submission = get_submission_by_id(db, submission_id)
        if not submission:
            logger.warning(f"Submission {submission_id} not found, skipping")
            continue
        if submission.status not in ["pending", "failed"]:
            logger.warning(f"Submission {submission_id} is not pending or failed (status: {submission.status}), skipping")
            continue
        valid_ids.append(submission_id)

    if not valid_ids:
        raise HTTPException(
            status_code=400,
            detail="No valid submissions to process (all not found or not pending/failed)"
        )

    # Process in background
    async def process_batch():
        manager = get_workflow_manager()
        for submission_id in valid_ids:
            if submission_id not in manager.processing_tasks or manager.processing_tasks[submission_id].done():
                task = asyncio.create_task(manager._process_submission(submission_id))
                manager.processing_tasks[submission_id] = task
                task.add_done_callback(lambda t, sid=submission_id: manager._cleanup_task(sid))
                await asyncio.sleep(0.5)

    if background_tasks:
        background_tasks.add_task(process_batch)
        return {
            "message": f"Processing {len(valid_ids)} submissions in background",
            "requested": len(submission_ids),
            "valid": len(valid_ids),
            "submission_ids": valid_ids
        }
    else:
        await process_batch()
        return {
            "message": f"Processed {len(valid_ids)} submissions",
            "requested": len(submission_ids),
            "valid": len(valid_ids),
            "submission_ids": valid_ids
        }
