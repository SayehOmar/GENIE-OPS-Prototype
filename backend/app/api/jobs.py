"""
Job/workflow API routes for managing submission jobs
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.db.crud import (
    get_saas_by_id,
    get_directories,
    get_submission_by_saas_directory,
    create_submission,
    get_submissions
)
from app.db.models import Submission, SubmissionCreate
from app.db.session import get_db
from app.core.security import get_current_user
from app.workflow.submitter import SubmissionWorkflow
from app.utils.logger import logger
from datetime import datetime

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
async def start_submission_job(
    job_request: StartJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Start a submission job for a SaaS product across multiple directories
    
    Creates submission records and queues them for processing.
    The actual submission workflow runs in the background.
    """
    # Verify SaaS exists
    saas = get_saas_by_id(db, job_request.saas_id)
    if not saas:
        raise HTTPException(status_code=404, detail="SaaS product not found")
    
    # Get directories to submit to
    if job_request.directory_ids:
        directories = [d for d in get_directories(db) if d.id in job_request.directory_ids]
        if len(directories) != len(job_request.directory_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more directory IDs not found"
            )
    else:
        # Submit to all directories
        directories = get_directories(db)
    
    if not directories:
        raise HTTPException(
            status_code=400,
            detail="No directories available for submission"
        )
    
    # Create submission records (skip if already exists)
    submissions_created = 0
    job_id = f"job_{saas.id}_{int(datetime.now().timestamp())}"
    
    for directory in directories:
        # Check if submission already exists
        existing = get_submission_by_saas_directory(
            db, 
            job_request.saas_id, 
            directory.id
        )
        
        if existing:
            logger.info(
                f"Submission already exists for SaaS {job_request.saas_id} "
                f"and directory {directory.id}, skipping"
            )
            continue
        
        # Create new submission record
        submission_data = SubmissionCreate(
            saas_id=job_request.saas_id,
            directory_id=directory.id,
            status="pending"
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
        status="queued"
    )


@router.get("/status/{saas_id}")
async def get_job_status(
    saas_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get submission job status for a SaaS product
    Returns summary of all submissions for the SaaS
    """
    # Verify SaaS exists
    saas = get_saas_by_id(db, saas_id)
    if not saas:
        raise HTTPException(status_code=404, detail="SaaS product not found")
    
    submissions = get_submissions(db, saas_id=saas_id)
    
    status_counts = {
        "pending": 0,
        "submitted": 0,
        "approved": 0,
        "failed": 0
    }
    
    for submission in submissions:
        status_counts[submission.status] = status_counts.get(submission.status, 0) + 1
    
    return {
        "saas_id": saas_id,
        "saas_name": saas.name,
        "total_submissions": len(submissions),
        "status_breakdown": status_counts,
        "submissions": submissions
    }
