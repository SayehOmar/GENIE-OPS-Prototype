"""
Database models
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


# SQLAlchemy ORM Models (must be defined before Pydantic models to avoid naming conflicts)
class SAAS(Base):
    __tablename__ = "saas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    contact_email = Column(String, nullable=False)
    logo_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    submissions = relationship("Submission", back_populates="saas")


class Directory(Base):
    __tablename__ = "directories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    saas_id = Column(Integer, ForeignKey("saas.id"), nullable=False)
    directory_id = Column(Integer, ForeignKey("directories.id"), nullable=False)
    status = Column(String, default="pending")  # pending, submitted, approved, failed
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    form_data = Column(Text, nullable=True)  # JSON string
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    saas = relationship("SAAS", back_populates="submissions")
    directory = relationship("Directory")


# Store ORM model references before Pydantic models shadow them
# These are used in CRUD operations to avoid naming conflicts
_SAAS_ORM = SAAS
_Directory_ORM = Directory
_Submission_ORM = Submission


# Pydantic models for request/response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SAASBase(BaseModel):
    name: str
    url: str
    description: Optional[str] = None
    category: Optional[str] = None
    contact_email: str
    logo_path: Optional[str] = None


class SAASCreate(SAASBase):
    pass


class SAASUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    contact_email: Optional[str] = None
    logo_path: Optional[str] = None


class SAAS(SAASBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DirectoryBase(BaseModel):
    name: str
    url: str
    description: Optional[str] = None


class Directory(DirectoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SubmissionBase(BaseModel):
    saas_id: int
    directory_id: int
    status: str = "pending"
    form_data: Optional[str] = None


class SubmissionCreate(SubmissionBase):
    pass


class SubmissionUpdate(BaseModel):
    status: Optional[str] = None
    submitted_at: Optional[datetime] = None
    error_message: Optional[str] = None
    form_data: Optional[str] = None
    retry_count: Optional[int] = None


class Submission(SubmissionBase):
    id: int
    submitted_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
