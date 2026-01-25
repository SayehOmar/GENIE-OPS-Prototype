"""
Submissions API routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.crud import (
    get_submissions,
    get_submission_by_id,
    create_submission,
    update_submission,
    delete_submission,
    get_submission_statistics,
    get_submission_by_saas_directory
)
from app.db.models import Submission, SubmissionCreate, SubmissionUpdate
from app.db.session import get_db
from app.core.security import get_current_user
from app.utils.rate_limit import limiter, get_rate_limit

router = APIRouter()


@router.get("/", response_model=List[Submission])
@limiter.limit(get_rate_limit("submissions"))
async def list_submissions(
    request: Request,
    saas_id: Optional[int] = Query(None, description="Filter by SaaS ID"),
    directory_id: Optional[int] = Query(None, description="Filter by Directory ID"),
    db: Session = Depends(get_db)
):
    """
    Get all submissions, optionally filtered by saas_id or directory_id.
    
    Args:
        saas_id: Optional filter to get submissions for a specific SaaS product
        directory_id: Optional filter to get submissions for a specific directory
        db: Database session dependency
        
    Returns:
        List of Submission objects matching the filters (or all if no filters)
    """
    return get_submissions(db, saas_id=saas_id, directory_id=directory_id)


@router.get("/{submission_id}", response_model=Submission)
async def get_submission(
    submission_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific submission by its ID.
    
    Args:
        submission_id: The unique ID of the submission to retrieve
        db: Database session dependency
        
    Returns:
        Submission object with all details including status, form_data, error_message
        
    Raises:
        HTTPException: 404 if submission not found
    """
    submission = get_submission_by_id(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.post("/", response_model=Submission)
async def create_submission_entry(
    submission_data: SubmissionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new submission record.
    
    This endpoint creates a submission record that will be processed by the workflow manager.
    The submission starts with status "pending" and will be automatically processed.
    
    Args:
        submission_data: SubmissionCreate object containing:
            - saas_id: ID of the SaaS product to submit
            - directory_id: ID of the directory to submit to
            - status: Initial status (defaults to "pending")
            - form_data: Optional JSON string with form structure
        db: Database session dependency
        
    Returns:
        Created Submission object with generated ID and timestamps
    """
    return create_submission(db, submission_data)


@router.put("/{submission_id}", response_model=Submission)
async def update_submission_entry(
    submission_id: int,
    submission_data: SubmissionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing submission record.
    
    Used to update submission status, error messages, form data, or retry count.
    Typically called by the workflow manager during processing.
    
    Args:
        submission_id: The unique ID of the submission to update
        submission_data: SubmissionUpdate object with fields to update:
            - status: New status (pending, submitted, approved, failed)
            - submitted_at: Timestamp when submission was completed
            - error_message: Error details if submission failed
            - form_data: JSON string with form structure and fill results
            - retry_count: Number of retry attempts
        db: Database session dependency
        
    Returns:
        Updated Submission object
        
    Raises:
        HTTPException: 404 if submission not found
    """
    submission = update_submission(db, submission_id, submission_data)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.delete("/{submission_id}")
async def delete_submission_entry(
    submission_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a submission record from the database.
    
    Permanently removes a submission record. Useful for cleaning up failed submissions
    that are no longer needed. This action cannot be undone.
    
    Args:
        submission_id: The unique ID of the submission to delete
        db: Database session dependency
        
    Returns:
        Success message confirming deletion
        
    Raises:
        HTTPException: 404 if submission not found
    """
    success = delete_submission(db, submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"message": "Submission deleted successfully"}


@router.get("/stats/summary")
async def get_submission_stats(
    saas_id: Optional[int] = Query(None, description="Filter statistics by SaaS ID"),
    db: Session = Depends(get_db)
):
    """
    Get submission statistics including counts by status and success rate.
    
    Calculates total submissions, breakdown by status (pending, submitted, approved, failed),
    and overall success rate. Includes processing submissions in pending count.
    Can be filtered by SaaS product ID.
    
    Args:
        saas_id: Optional filter to get statistics for a specific SaaS product
        db: Database session dependency
        
    Returns:
        Dictionary containing:
            - total: Total number of submissions
            - pending: Count of pending submissions (includes processing)
            - processing: Count of currently processing submissions
            - submitted: Count of successfully submitted entries
            - approved: Count of approved submissions
            - failed: Count of failed submissions
            - success_rate: Percentage of successful submissions (submitted + approved)
            - by_status: Breakdown by status for compatibility
    """
    from app.workflow.manager import get_workflow_manager
    
    # Get base stats from database
    stats = get_submission_statistics(db, saas_id=saas_id)
    
    # Get active processing submissions from workflow manager
    manager = get_workflow_manager()
    active_submission_ids = manager.get_status().get("active_submission_ids", [])
    processing_count = len(active_submission_ids)
    
    # If filtering by saas_id, filter active submissions too
    if saas_id and active_submission_ids:
        active_submissions = [get_submission_by_id(db, sid) for sid in active_submission_ids]
        active_submissions = [s for s in active_submissions if s and s.saas_id == saas_id]
        processing_count = len(active_submissions)
    
    # Add processing count to stats
    stats["processing"] = processing_count
    
    # Recalculate success rate excluding pending/processing from denominator
    completed_count = stats["submitted"] + stats["approved"] + stats["failed"]
    if completed_count > 0:
        success_count = stats["submitted"] + stats["approved"]
        stats["success_rate"] = round((success_count / completed_count) * 100, 2)
    else:
        stats["success_rate"] = 0.0
    
    # Add by_status for compatibility with existing frontend code
    stats["by_status"] = {
        "pending": stats["pending"],
        "submitted": stats["submitted"],
        "approved": stats["approved"],
        "failed": stats["failed"],
        "processing": stats["processing"]
    }
    
    return stats


@router.post("/{submission_id}/retry")
@limiter.limit(get_rate_limit("submissions"))
async def retry_submission(
    request: Request,
    submission_id: int,
    db: Session = Depends(get_db)
):
    """
    Retry a failed or pending submission.
    
    Resets the submission status to "pending" and increments the retry count.
    The workflow manager will automatically pick up and process the submission
    in the next processing cycle. Clears any previous error messages.
    
    Args:
        submission_id: The unique ID of the submission to retry
        db: Database session dependency
        
    Returns:
        Dictionary containing:
            - message: Success message
            - submission: Updated submission object
            - retry_count: New retry count after increment
            
    Raises:
        HTTPException: 404 if submission not found
        HTTPException: 400 if submission status is not "failed" or "pending"
    """
    submission = get_submission_by_id(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.status not in ["failed", "pending"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry submission with status: {submission.status}"
        )
    
    # Reset to pending and increment retry count
    update_data = SubmissionUpdate(
        status="pending",
        retry_count=submission.retry_count + 1,
        error_message=None
    )
    
    updated_submission = update_submission(db, submission_id, update_data)
    return {
        "message": "Submission queued for retry",
        "submission": updated_submission,
        "retry_count": updated_submission.retry_count
    }
