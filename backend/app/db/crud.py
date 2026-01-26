"""
CRUD operations for database models
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app.db import models

# Import SQLAlchemy ORM models using the stored references (before Pydantic models shadow them)
from app.db.models import (
    _SAAS_ORM as SAASORM,
    _Directory_ORM as DirectoryORM,
    _Submission_ORM as SubmissionORM,
)


# SAAS CRUD
def get_saas_list(db: Session) -> List[SAASORM]:
    """
    Get all SaaS entries
    """
    return db.query(SAASORM).all()


def get_saas_by_id(db: Session, saas_id: int) -> Optional[SAASORM]:
    """
    Get a SaaS entry by ID
    """
    return db.query(SAASORM).filter(SAASORM.id == saas_id).first()


def create_saas(db: Session, saas_data: models.SAASCreate) -> SAASORM:
    """
    Create a new SaaS entry
    """
    # Convert Pydantic model to dict
    saas_dict = saas_data.model_dump()
    # Use SQLAlchemy ORM model (imported as SAASORM to avoid conflict)
    db_saas = SAASORM(
        name=saas_dict["name"],
        url=saas_dict["url"],
        description=saas_dict.get("description"),
        category=saas_dict.get("category"),
        contact_email=saas_dict["contact_email"],
        logo_path=saas_dict.get("logo_path"),
    )
    db.add(db_saas)
    db.commit()
    db.refresh(db_saas)
    return db_saas


def update_saas(
    db: Session, saas_id: int, saas_data: models.SAASUpdate
) -> Optional[SAASORM]:
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
def get_directories(db: Session) -> List[DirectoryORM]:
    """
    Get all directories
    """
    return db.query(DirectoryORM).all()


def get_directory_by_id(db: Session, directory_id: int) -> Optional[DirectoryORM]:
    """
    Get a directory by ID
    """
    return db.query(DirectoryORM).filter(DirectoryORM.id == directory_id).first()


def _fix_directories_sequence(db: Session) -> None:
    """
    Fix the PostgreSQL sequence for directories.id if it's out of sync.
    This happens when data is inserted manually or sequences get out of sync.
    """
    try:
        # Get the maximum ID currently in the table
        result = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM directories"))
        max_id = result.scalar() or 0
        
        # Reset the sequence to the next value after the max ID
        db.execute(text(f"SELECT setval('directories_id_seq', {max_id + 1}, false)"))
        db.commit()
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to fix directories sequence: {str(e)}")


def create_directory(db: Session, directory_data: models.DirectoryBase) -> DirectoryORM:
    """
    Create a new directory.
    Automatically fixes sequence issues if they occur.
    """
    db_directory = DirectoryORM(
        name=directory_data.name,
        url=directory_data.url,
        description=directory_data.description,
    )
    db.add(db_directory)
    
    try:
        db.commit()
        db.refresh(db_directory)
        return db_directory
    except IntegrityError as e:
        db.rollback()
        # Check if it's a sequence issue (duplicate key on primary key)
        if "duplicate key value violates unique constraint" in str(e) and "directories_pkey" in str(e):
            # Fix the sequence and retry
            _fix_directories_sequence(db)
            # Retry the insert
            db.add(db_directory)
            db.commit()
            db.refresh(db_directory)
            return db_directory
        else:
            # Re-raise if it's a different integrity error
            raise


def update_directory(
    db: Session, directory_id: int, directory_data: models.DirectoryBase
) -> Optional[DirectoryORM]:
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
def get_submissions(
    db: Session,
    saas_id: Optional[int] = None,
    directory_id: Optional[int] = None,
    status: Optional[str] = None,
) -> List[SubmissionORM]:
    """
    Get all submissions, optionally filtered by saas_id, directory_id, or status
    """
    query = db.query(SubmissionORM)

    if saas_id:
        query = query.filter(SubmissionORM.saas_id == saas_id)
    if directory_id:
        query = query.filter(SubmissionORM.directory_id == directory_id)
    if status:
        query = query.filter(SubmissionORM.status == status)

    return query.all()


def get_submission_by_id(db: Session, submission_id: int) -> Optional[SubmissionORM]:
    """
    Get a submission by ID
    """
    return db.query(SubmissionORM).filter(SubmissionORM.id == submission_id).first()


def get_submission_by_saas_directory(
    db: Session, saas_id: int, directory_id: int
) -> Optional[SubmissionORM]:
    """
    Get a submission by saas_id and directory_id (to check for duplicates)
    """
    return (
        db.query(SubmissionORM)
        .filter(
            and_(
                SubmissionORM.saas_id == saas_id,
                SubmissionORM.directory_id == directory_id,
            )
        )
        .first()
    )


def create_submission(
    db: Session, submission_data: models.SubmissionCreate
) -> SubmissionORM:
    """
    Create a new submission
    """
    db_submission = SubmissionORM(
        saas_id=submission_data.saas_id,
        directory_id=submission_data.directory_id,
        status=submission_data.status,
        form_data=submission_data.form_data,
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


def update_submission(
    db: Session, submission_id: int, submission_data: models.SubmissionUpdate
) -> Optional[SubmissionORM]:
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
    query = db.query(SubmissionORM)
    if saas_id:
        query = query.filter(SubmissionORM.saas_id == saas_id)

    total = query.count()
    pending = query.filter(SubmissionORM.status == "pending").count()
    submitted = query.filter(SubmissionORM.status == "submitted").count()
    approved = query.filter(SubmissionORM.status == "approved").count()
    # Count both "failed" and "auto_retry_failed_{x}" as failed
    failed = query.filter(
        (SubmissionORM.status == "failed") | 
        (SubmissionORM.status.like("auto_retry_failed_%"))
    ).count()

    success_rate = 0.0
    if total > 0:
        success_count = (
            approved + submitted
        )  # Consider both approved and submitted as success
        success_rate = (success_count / total) * 100

    return {
        "total": total,
        "pending": pending,
        "submitted": submitted,
        "approved": approved,
        "failed": failed,
        "success_rate": round(success_rate, 2),
    }
