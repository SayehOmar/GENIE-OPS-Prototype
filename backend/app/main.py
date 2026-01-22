"""
FastAPI entry point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.workflow.manager import get_workflow_manager
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting GENIE OPS API...")
    workflow_manager = get_workflow_manager()
    await workflow_manager.start()
    logger.info("Workflow manager started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GENIE OPS API...")
    await workflow_manager.stop()
    logger.info("Workflow manager stopped")


app = FastAPI(
    title="GENIE OPS API",
    description="Automated SaaS form submission system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - must be added before routes
# Configure to handle redirects properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
from app.api import auth, saas, directories, submissions, jobs, testing

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(saas.router, prefix="/api/saas", tags=["saas"])
app.include_router(directories.router, prefix="/api/directories", tags=["directories"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["submissions"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(testing.router, prefix="/api/testing", tags=["testing"])


@app.get("/")
async def root():
    return {"message": "GENIE OPS API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
