"""
Directory-related API routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.crud import get_directories
from app.db.models import Directory
from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[Directory])
async def list_directories(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all directories
    """
    return await get_directories(db)
