"""FastAPI application entry point for AgenticFleet.

This module initializes the FastAPI application, configures middleware,
and registers API routers for workflow execution, agent management, history,
and streaming chat.
"""

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentic_fleet.app.dependencies import lifespan
from agentic_fleet.app.routers import agents, dspy_management, history, streaming, workflow

# =============================================================================
# Logging Configuration
# =============================================================================


def _configure_logging() -> None:
    """Configure real-time console logging for the API.

    Sets up structured logging with timestamps that flush immediately
    to stdout for real-time visibility.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # Create a handler that writes to stdout with immediate flushing
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level, logging.INFO))
    handler.setFormatter(logging.Formatter(log_format, datefmt="%H:%M:%S"))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers to prevent duplicates
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)

    root_logger.addHandler(handler)

    # Also configure uvicorn access logs
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = [handler]

    # Reduce noise from some verbose libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


# Initialize logging before app creation
_configure_logging()
logger = logging.getLogger(__name__)


def _get_allowed_origins() -> list[str]:
    """Get allowed CORS origins from environment.

    Returns:
        List of allowed origin URLs.
    """
    origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
    return [o.strip() for o in origins.split(",") if o.strip()]


app = FastAPI(
    title="AgenticFleet API",
    description="API for AgenticFleet Supervisor Workflow with streaming support",
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Versioned API routes
app.include_router(workflow.router, prefix="/api/v1", tags=["workflow"])
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(dspy_management.router, prefix="/api/v1", tags=["dspy"])

# Streaming routes at /api (no version) for frontend compatibility
# Frontend expects POST /api/chat for streaming
app.include_router(streaming.router, prefix="/api", tags=["chat"])


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        dict with status "ok" if the service is running.
    """
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def readiness_check() -> dict[str, str | bool]:
    """Readiness check endpoint.

    Returns:
        dict with status and workflow availability.
    """
    workflow_ready = hasattr(app.state, "workflow") and app.state.workflow is not None
    return {"status": "ready" if workflow_ready else "initializing", "workflow": workflow_ready}


# Log registered routes on module load
logger.info("AgenticFleet API v0.3.0 initialized")
logger.info(f"CORS origins: {_get_allowed_origins()}")
