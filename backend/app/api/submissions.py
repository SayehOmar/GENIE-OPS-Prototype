"""
Submissions API routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.crud import (
    get_submissions,
    get_submission_by_id,
    create_submission,
    update_submission,
    delete_submission
)
from app.db.models import Submission, SubmissionCreate, SubmissionUpdate
from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[Submission])
async def list_submissions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all submissions
    """
    return await get_submissions(db)


@router.get("/{submission_id}", response_model=Submission)
async def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific submission by ID
    """
    submission = await get_submission_by_id(db, submission_id)
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
    return await create_submission(db, submission_data)


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
    submission = await update_submission(db, submission_id, submission_data)
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
    success = await delete_submission(db, submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"message": "Submission deleted successfully"}
