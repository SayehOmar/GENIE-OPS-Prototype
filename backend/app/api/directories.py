"""
Directory-related API routes
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from app.db.crud import (
    get_directories,
    get_directory_by_id,
    create_directory,
    update_directory,
    delete_directory
)
from app.db.models import Directory, DirectoryBase
from app.db.session import get_db
from app.core.security import get_current_user
from app.utils.rate_limit import limiter, get_rate_limit

router = APIRouter()


@router.get("/", response_model=List[Directory])
async def list_directories(
    db: Session = Depends(get_db)
):
    """
    Get all directories
    """
    return get_directories(db)


@router.get("/{directory_id}", response_model=Directory)
async def get_directory(
    directory_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific directory by ID
    """
    directory = get_directory_by_id(db, directory_id)
    if not directory:
        raise HTTPException(status_code=404, detail="Directory not found")
    return directory


@router.post("/", response_model=Directory)
async def create_directory_entry(
    directory_data: DirectoryBase,
    db: Session = Depends(get_db)
):
    """
    Create a new directory
    """
    try:
        return create_directory(db, directory_data)
    except IntegrityError as e:
        # Handle database integrity errors
        error_msg = str(e)
        if "duplicate key value violates unique constraint" in error_msg:
            if "directories_pkey" in error_msg:
                raise HTTPException(
                    status_code=500,
                    detail="Database sequence error. The sequence has been automatically fixed. Please try again."
                )
            else:
                # Other unique constraint violations (e.g., duplicate name or URL)
                raise HTTPException(
                    status_code=400,
                    detail="A directory with this name or URL already exists."
                )
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {error_msg}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create directory: {str(e)}"
        )


@router.put("/{directory_id}", response_model=Directory)
async def update_directory_entry(
    directory_id: int,
    directory_data: DirectoryBase,
    db: Session = Depends(get_db)
):
    """
    Update an existing directory
    """
    directory = update_directory(db, directory_id, directory_data)
    if not directory:
        raise HTTPException(status_code=404, detail="Directory not found")
    return directory


@router.delete("/{directory_id}")
async def delete_directory_entry(
    directory_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a directory
    """
    success = delete_directory(db, directory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Directory not found")
    return {"message": "Directory deleted successfully"}
