"""FastAPI application entry point for AgenticFleet.

This module initializes the FastAPI application, configures middleware,
and registers API routers for workflow execution, agent management, history,
and streaming chat.
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from agentic_fleet.app.dependencies import lifespan
from agentic_fleet.app.middleware import RequestIDMiddleware
from agentic_fleet.app.routers import (
    api,
    conversations,
    dspy_management,
    history,
    nlu,
    sessions,
    streaming,
)
from agentic_fleet.app.settings import get_settings

# =============================================================================
# Logging Configuration
# =============================================================================


def _configure_logging() -> None:
    """Configure real-time console logging for the API.

    Sets up structured logging with timestamps that flush immediately
    to stdout for real-time visibility.
    """
    settings = get_settings()
    log_level = settings.log_level
    structured = settings.log_json
    log_format = settings.log_format

    # Create a handler that writes to stdout with immediate flushing
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level, logging.INFO))

    if structured:
        # Emit JSON logs for easier ingestion (e.g., Datadog, Loki)
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(module)s %(lineno)d",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "message": "msg",
            },
        )
    else:
        formatter = logging.Formatter(log_format, datefmt="%H:%M:%S")

    handler.setFormatter(formatter)

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

    # Reduce noise from verbose libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
    logging.getLogger("azure.monitor").setLevel(logging.WARNING)

    # Suppress DSPy adapter fallback warnings (expected behavior when model
    # doesn't support structured outputs - graceful fallback to JSON mode)
    logging.getLogger("dspy.adapters.json_adapter").setLevel(logging.ERROR)


# Initialize logging before app creation
_configure_logging()
logger = logging.getLogger(__name__)


def _get_allowed_origins() -> list[str]:
    """Get allowed CORS origins from environment.

    Returns:
        List of allowed origin URLs.
    """
    return get_settings().cors_allowed_origins


app = FastAPI(
    title=get_settings().app_name,
    description="API for AgenticFleet Supervisor Workflow with streaming support",
    version=get_settings().app_version,
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

# Attach request IDs for traceability
app.add_middleware(RequestIDMiddleware)  # type: ignore[arg-type]

# Versioned API routes
app.include_router(api.api_router, prefix="/api/v1", tags=["workflow", "agents"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(dspy_management.router, prefix="/api/v1", tags=["dspy"])
app.include_router(nlu.router, prefix="/api/v1", tags=["nlu"])
app.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])

# Streaming routes at /api (no version) for frontend compatibility
# Frontend expects POST /api/chat for streaming
app.include_router(streaming.router, prefix="/api", tags=["chat"])


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str | dict[str, str]]:
    """Enhanced health check with dependency verification.

    Returns:
        dict with overall status, individual checks, and version.
    """
    from agentic_fleet.app.dependencies import get_conversation_manager

    checks = {
        "api": "ok",
        "workflow": "ok" if getattr(app.state, "workflow", None) else "error",
        "session_manager": "ok" if getattr(app.state, "session_manager", None) else "error",
    }

    # Check conversation manager
    try:
        conv_mgr = get_conversation_manager()
        checks["conversations"] = "ok" if conv_mgr else "error"
    except Exception:
        checks["conversations"] = "error"

    # Determine overall status
    all_ok = all(v == "ok" for v in checks.values())
    status = "ok" if all_ok else "degraded"

    return {
        "status": status,
        "checks": checks,
        "version": get_settings().app_version,
    }


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
