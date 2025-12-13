"""FastAPI application entry point for AgenticFleet.

This module follows the FastAPI full-stack template structure:
- `agentic_fleet/main.py` creates the FastAPI app (this file)
- `agentic_fleet/api/main.py` aggregates versioned API routers
- `agentic_fleet/api/deps.py` provides dependency injection helpers
"""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from agentic_fleet.api.lifespan import lifespan
from agentic_fleet.api.main import api_router
from agentic_fleet.api.middleware import RequestIDMiddleware
from agentic_fleet.api.routes import chat as chat_routes
from agentic_fleet.core.settings import get_settings
from agentic_fleet.utils.tracing import initialize_tracing


def _configure_logging() -> None:
    """Configure application console logging.

    Uses JSON logs by default (LOG_JSON=1) for easier ingestion.
    """
    settings = get_settings()
    log_level = settings.log_level
    structured = settings.log_json
    log_format = settings.log_format

    # Initialize tracing early (no-op unless enabled)
    initialize_tracing()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level, logging.INFO))

    if structured:
        formatter = jsonlogger.JsonFormatter(  # type: ignore[attr-defined]
            "%(asctime)s %(levelname)s %(name)s %(message)s %(module)s %(lineno)d",
            rename_fields={"asctime": "timestamp", "levelname": "level", "message": "msg"},
        )
    else:
        formatter = logging.Formatter(log_format, datefmt="%H:%M:%S")

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers to prevent duplicates (e.g. in reload)
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)

    root_logger.addHandler(handler)

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
    logging.getLogger("dspy.adapters.json_adapter").setLevel(logging.ERROR)


_configure_logging()
logger = logging.getLogger(__name__)


def _get_allowed_origins() -> list[str]:
    return get_settings().cors_allowed_origins


app = FastAPI(
    title=get_settings().app_name,
    description="AgenticFleet API (DSPy + Microsoft Agent Framework)",
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

app.add_middleware(RequestIDMiddleware)  # type: ignore[arg-type]

# Versioned API routes
app.include_router(api_router, prefix="/api/v1")

# Streaming routes at /api (no version) for frontend compatibility
app.include_router(chat_routes.router, prefix="/api", tags=["chat"])


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, object]:
    """Health check with basic dependency verification."""
    checks = {
        "api": "ok",
        "workflow": "ok" if getattr(app.state, "workflow", None) else "error",
        "session_manager": "ok" if getattr(app.state, "session_manager", None) else "error",
        "conversation_manager": "ok"
        if getattr(app.state, "conversation_manager", None)
        else "error",
    }
    status_value = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status_value, "checks": checks, "version": get_settings().app_version}


@app.get("/ready", tags=["health"])
async def readiness_check() -> dict[str, object]:
    """Readiness check indicating whether the workflow is initialized."""
    workflow_ready = getattr(app.state, "workflow", None) is not None
    return {"status": "ready" if workflow_ready else "initializing", "workflow": workflow_ready}


logger.info("AgenticFleet API initialized (version=%s)", get_settings().app_version)
logger.info("CORS origins: %s", _get_allowed_origins())
