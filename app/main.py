"""FastAPI application entry point."""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from logs_config.config import setup_logging

# Import admin router (load_dotenv is called inside admin.py)
from api.admin import router as admin_router

# Import agent router (load_dotenv is called inside agent.py)
from api.agent import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include admin router
app.include_router(admin_router, prefix=settings.api_prefix)

# Include agent router
app.include_router(agent_router, prefix=settings.api_prefix)


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.perf_counter()

    # Log request
    logger.bind(
        request_id=request_id,
        endpoint=str(request.url.path),
        method=request.method,
    ).info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Log response
    duration = time.perf_counter() - start_time
    logger.bind(
        request_id=request_id,
        endpoint=str(request.url.path),
        method=request.method,
        status_code=response.status_code,
        duration=f"{duration:.3f}s",
    ).info(
        f"Response: {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)"
    )

    return response


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
