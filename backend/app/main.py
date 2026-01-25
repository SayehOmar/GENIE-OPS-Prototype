"""
FastAPI entry point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.workflow.manager import get_workflow_manager
from app.automation.browser_pool import start_browser_pool, stop_browser_pool
from app.utils.logger import logger, print_color_legend
from app.utils.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Print color legend on startup
    print_color_legend()
    
    # Startup
    logger.info("Starting GENIE OPS API...")
    
    # Start browser worker pool (for Windows threading isolation)
    try:
        start_browser_pool()
        logger.info("Browser worker pool started")
    except Exception as e:
        logger.warning(f"Failed to start browser worker pool: {e}. Will use direct Playwright.")
    
    # Start workflow manager
    workflow_manager = get_workflow_manager()
    await workflow_manager.start()
    logger.info("Workflow manager started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GENIE OPS API...")
    
    # Stop workflow manager first
    await workflow_manager.stop()
    logger.info("Workflow manager stopped")
    
    # Stop browser worker pool
    try:
        stop_browser_pool()
        logger.info("Browser worker pool stopped")
    except Exception as e:
        logger.warning(f"Error stopping browser worker pool: {e}")


app = FastAPI(
    title="GENIE OPS API",
    description="Automated SaaS form submission system",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

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
@limiter.limit("100/minute")
async def root(request: Request):
    return {"message": "GENIE OPS API", "version": "1.0.0"}


@app.get("/health")
@limiter.limit("200/minute")
async def health(request: Request):
    return {"status": "healthy"}
