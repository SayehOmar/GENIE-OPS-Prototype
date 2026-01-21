"""
Database session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Important: do NOT attempt a DB connection at import-time.
# If credentials/DB are not ready, that would crash Uvicorn before the API can even start.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Database session dependency
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
