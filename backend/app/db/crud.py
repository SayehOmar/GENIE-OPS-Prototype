"""
CRUD operations for database models
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app.db import models


# SAAS CRUD
def get_saas_list(db: Session) -> List[models.SAAS]:
    """
    Get all SaaS entries
    """
    return db.query(models.SAAS).all()


def get_saas_by_id(db: Session, saas_id: int) -> Optional[models.SAAS]:
    """
    Get a SaaS entry by ID
    """
    return db.query(models.SAAS).filter(models.SAAS.id == saas_id).first()


def create_saas(db: Session, saas_data: models.SAASCreate) -> models.SAAS:
    """
    Create a new SaaS entry
    """
    db_saas = models.SAAS(
        name=saas_data.name,
        url=saas_data.url,
        description=saas_data.description,
        category=saas_data.category,
        contact_email=saas_data.contact_email,
        logo_path=saas_data.logo_path
    )
    db.add(db_saas)
    db.commit()
    db.refresh(db_saas)
    return db_saas


def update_saas(db: Session, saas_id: int, saas_data: models.SAASUpdate) -> Optional[models.SAAS]:
    """
    Update an existing SaaS entry
    """
    db_saas = get_saas_by_id(db, saas_id)
    if not db_saas:
        return None
    
    update_data = saas_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_saas, field, value)
    
    db.commit()
    db.refresh(db_saas)
    return db_saas


def delete_saas(db: Session, saas_id: int) -> bool:
    """
    Delete a SaaS entry
    """
    db_saas = get_saas_by_id(db, saas_id)
    if not db_saas:
        return False
    
    db.delete(db_saas)
    db.commit()
    return True


# Directory CRUD
def get_directories(db: Session) -> List[models.Directory]:
    """
    Get all directories
    """
    return db.query(models.Directory).all()


def get_directory_by_id(db: Session, directory_id: int) -> Optional[models.Directory]:
    """
    Get a directory by ID
    """
    return db.query(models.Directory).filter(models.Directory.id == directory_id).first()


def create_directory(db: Session, directory_data: models.DirectoryBase) -> models.Directory:
    """
    Create a new directory
    """
    db_directory = models.Directory(
        name=directory_data.name,
        url=directory_data.url,
        description=directory_data.description
    )
    db.add(db_directory)
    db.commit()
    db.refresh(db_directory)
    return db_directory


def update_directory(db: Session, directory_id: int, directory_data: models.DirectoryBase) -> Optional[models.Directory]:
    """
    Update an existing directory
    """
    db_directory = get_directory_by_id(db, directory_id)
    if not db_directory:
        return None
    
    update_data = directory_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_directory, field, value)
    
    db.commit()
    db.refresh(db_directory)
    return db_directory


def delete_directory(db: Session, directory_id: int) -> bool:
    """
    Delete a directory
    """
    db_directory = get_directory_by_id(db, directory_id)
    if not db_directory:
        return False
    
    db.delete(db_directory)
    db.commit()
    return True


# Submission CRUD
def get_submissions(db: Session, saas_id: Optional[int] = None, directory_id: Optional[int] = None) -> List[models.Submission]:
    """
    Get all submissions, optionally filtered by saas_id or directory_id
    """
    query = db.query(models.Submission)
    
    if saas_id:
        query = query.filter(models.Submission.saas_id == saas_id)
    if directory_id:
        query = query.filter(models.Submission.directory_id == directory_id)
    
    return query.all()


def get_submission_by_id(db: Session, submission_id: int) -> Optional[models.Submission]:
    """
    Get a submission by ID
    """
    return db.query(models.Submission).filter(models.Submission.id == submission_id).first()


def get_submission_by_saas_directory(db: Session, saas_id: int, directory_id: int) -> Optional[models.Submission]:
    """
    Get a submission by saas_id and directory_id (to check for duplicates)
    """
    return db.query(models.Submission).filter(
        and_(
            models.Submission.saas_id == saas_id,
            models.Submission.directory_id == directory_id
        )
    ).first()


def create_submission(db: Session, submission_data: models.SubmissionCreate) -> models.Submission:
    """
    Create a new submission
    """
    db_submission = models.Submission(
        saas_id=submission_data.saas_id,
        directory_id=submission_data.directory_id,
        status=submission_data.status,
        form_data=submission_data.form_data
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


def update_submission(db: Session, submission_id: int, submission_data: models.SubmissionUpdate) -> Optional[models.Submission]:
    """
    Update an existing submission
    """
    db_submission = get_submission_by_id(db, submission_id)
    if not db_submission:
        return None
    
    update_data = submission_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_submission, field, value)
    
    db.commit()
    db.refresh(db_submission)
    return db_submission


def delete_submission(db: Session, submission_id: int) -> bool:
    """
    Delete a submission
    """
    db_submission = get_submission_by_id(db, submission_id)
    if not db_submission:
        return False
    
    db.delete(db_submission)
    db.commit()
    return True


# Statistics and helper functions
def get_submission_statistics(db: Session, saas_id: Optional[int] = None) -> dict:
    """
    Get submission statistics (counts by status, success rate)
    """
    query = db.query(models.Submission)
    if saas_id:
        query = query.filter(models.Submission.saas_id == saas_id)
    
    total = query.count()
    pending = query.filter(models.Submission.status == "pending").count()
    submitted = query.filter(models.Submission.status == "submitted").count()
    approved = query.filter(models.Submission.status == "approved").count()
    failed = query.filter(models.Submission.status == "failed").count()
    
    success_rate = 0.0
    if total > 0:
        success_count = approved + submitted  # Consider both approved and submitted as success
        success_rate = (success_count / total) * 100
    
    return {
        "total": total,
        "pending": pending,
        "submitted": submitted,
        "approved": approved,
        "failed": failed,
        "success_rate": round(success_rate, 2)
    }
