"""
FastAPI entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title="GENIE OPS API",
    description="Automated SaaS form submission system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.api import auth, saas, directories, submissions, jobs

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(saas.router, prefix="/api/saas", tags=["saas"])
app.include_router(directories.router, prefix="/api/directories", tags=["directories"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["submissions"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])


@app.get("/")
async def root():
    return {"message": "GENIE OPS API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
