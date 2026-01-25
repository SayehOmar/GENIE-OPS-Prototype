"""
SaaS-related API routes
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.db.crud import (
    get_saas_list,
    get_saas_by_id,
    create_saas,
    update_saas,
    delete_saas,
)
from app.db.models import SAAS, SAASCreate, SAASUpdate
from app.db.session import get_db
from app.core.security import get_current_user
from app.utils.rate_limit import limiter, get_rate_limit

router = APIRouter()


@router.get("", response_model=List[SAAS])  # Remove trailing slash to avoid redirect
@router.get("/", response_model=List[SAAS])
async def list_saas(db: Session = Depends(get_db)):
    """
    Get all SaaS entries
    """
    return get_saas_list(db)


@router.get("/{saas_id}", response_model=SAAS)
async def get_saas(saas_id: int, db: Session = Depends(get_db)):
    """
    Get a specific SaaS entry by ID
    """
    saas = get_saas_by_id(db, saas_id)
    if not saas:
        raise HTTPException(status_code=404, detail="SaaS entry not found")
    return saas


@router.post("", response_model=SAAS)  # Remove trailing slash to avoid redirect
@router.post("/", response_model=SAAS)
async def create_saas_entry(saas_data: SAASCreate, db: Session = Depends(get_db)):
    """
    Create a new SaaS entry
    """
    return create_saas(db, saas_data)


@router.put("/{saas_id}", response_model=SAAS)
async def update_saas_entry(
    saas_id: int, saas_data: SAASUpdate, db: Session = Depends(get_db)
):
    """
    Update an existing SaaS entry
    """
    saas = update_saas(db, saas_id, saas_data)
    if not saas:
        raise HTTPException(status_code=404, detail="SaaS entry not found")
    return saas


@router.delete("/{saas_id}")
async def delete_saas_entry(saas_id: int, db: Session = Depends(get_db)):
    """
    Delete a SaaS entry
    """
    success = delete_saas(db, saas_id)
    if not success:
        raise HTTPException(status_code=404, detail="SaaS entry not found")
    return {"message": "SaaS entry deleted successfully"}
