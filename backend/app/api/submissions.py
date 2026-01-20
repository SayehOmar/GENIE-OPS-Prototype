"""
Submissions API routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter()


@router.get("/", response_model=List[Submission])
async def list_submissions(
    saas_id: Optional[int] = Query(None, description="Filter by SaaS ID"),
    directory_id: Optional[int] = Query(None, description="Filter by Directory ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all submissions, optionally filtered by saas_id or directory_id
    """
    return get_submissions(db, saas_id=saas_id, directory_id=directory_id)


@router.get("/{submission_id}", response_model=Submission)
async def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific submission by ID
    """
    submission = get_submission_by_id(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.post("/", response_model=Submission)
async def create_submission_entry(
    submission_data: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new submission
    """
    return create_submission(db, submission_data)


@router.put("/{submission_id}", response_model=Submission)
async def update_submission_entry(
    submission_id: int,
    submission_data: SubmissionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing submission
    """
    submission = update_submission(db, submission_id, submission_data)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.delete("/{submission_id}")
async def delete_submission_entry(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a submission
    """
    success = delete_submission(db, submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"message": "Submission deleted successfully"}


@router.get("/stats/summary")
async def get_submission_stats(
    saas_id: Optional[int] = Query(None, description="Filter statistics by SaaS ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get submission statistics (counts by status, success rate)
    """
    return get_submission_statistics(db, saas_id=saas_id)


@router.post("/{submission_id}/retry")
async def retry_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retry a failed submission
    Resets status to pending and increments retry count
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
