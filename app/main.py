import os
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.logger import app_logger, log_request_start, log_request_end, log_request_error
from app.db.db import init_db, close_db, ping_database
from app.db.seed import ensure_seed_admin_user
from app.api.auth.router import router as auth_router
from app.api.rjm.router import router as rjm_router


_git_sha_cache: Optional[str] = None


def get_git_sha() -> str:
    """Get the current Git commit SHA (cached to avoid blocking)."""
    global _git_sha_cache
    if _git_sha_cache is not None:
        return _git_sha_cache
    
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=1.0
        )
        _git_sha_cache = result.stdout.strip()[:8]
        return _git_sha_cache
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        _git_sha_cache = "local-dev"
        return _git_sha_cache


@asynccontextmanager

async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    # Startup
    app_logger.info("RJM Backend Core API starting up")
    app_logger.info("Application initialized successfully")
    app_logger.info("Logging system active - logs will be saved to logs/ directory")
    # Initialize database + seed user
    try:
        await init_db()
        await ensure_seed_admin_user()
    except Exception as e:
        app_logger.error(f"Failed to initialize database: {e}")
    
    yield
    
    # Shutdown
    try:
        await close_db()
    except Exception as e:
        app_logger.error(f"Failed to close database: {e}")
    app_logger.info("RJM Backend Core API shutting down")
    app_logger.info("Application shutdown complete")


app = FastAPI(
    title="RJM Backend Core",
    description="RJM MIRA backend core API",
    version="1.0.0",
    author="CorpusAI Development Team",
    author_email="dev@corpusai.com",
    contact={
        "name": "CorpusAI Support",
        "url": "https://www.corpusiq.io/support",
        "email": "support@corpusai.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    terms_of_service="https://www.corpusiq.io/compliance",
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server",
        },
        {
            "url": "https://api.corpusai.com",
            "description": "Production server",
        },
    ],
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Add PRODUCTION DOMAINS HERE
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing information using Loguru."""
    start_time = datetime.now()
    
    # Log request start
    log_request_start(request)
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (datetime.now() - start_time).total_seconds()
        
        # Log response
        log_request_end(request, response.status_code, process_time)
        
        return response
        
    except Exception as e:
        # Log error
        process_time = (datetime.now() - start_time).total_seconds()
        log_request_error(request, e, process_time)
        raise


@app.get("/", tags=["health"])
async def root():
    """Root endpoint with basic API information."""
    app_logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to RJM Backend Core API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/status", tags=["health"])
async def status():
    """Status endpoint with build information for CI/CD monitoring."""
    app_logger.info("Status endpoint accessed")
    
    # Get build information from environment variables (CI-injected)
    build_number = os.getenv("BUILD_NUMBER", "local-dev")
    git_sha = os.getenv("GIT_SHA", os.getenv("GITHUB_SHA", get_git_sha()))
    environment = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))
    
    return {
        "status": "ok",
        "build": build_number,
        "sha": git_sha,
        "env": environment
    }


@app.get("/health/db", tags=["health"])
async def health_db():
    """Database health endpoint: returns 200 if DB responds to SELECT 1."""
    is_ok, message = await ping_database()
    if not is_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unavailable", "message": message}
        )
    return {"status": "ok", "db": "available", "message": message}


# Include API routers
app.include_router(auth_router)
app.include_router(rjm_router)



if __name__ == "__main__":
    import uvicorn
    
    # Log startup
    app_logger.info("Starting RJM Backend Core API server")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config=None  # Use our custom logger
    )
