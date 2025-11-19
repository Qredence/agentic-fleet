"""Main FastAPI application for Agentic Fleet."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agentic_fleet.api.exceptions import AgenticFleetAPIError
from agentic_fleet.api.middlewares import LoggingMiddleware, RequestIDMiddleware
from agentic_fleet.api.routes import health, workflow
from agentic_fleet.utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events.

    Args:
        app: The FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info("Starting Agentic Fleet API v0.6.0")
    logger.info("API documentation available at /api/docs")

    yield

    # Shutdown
    logger.info("Shutting down Agentic Fleet API")


# Create FastAPI application
app = FastAPI(
    title="Agentic Fleet API",
    description=(
        "API for orchestrating autonomous agents with DSPy and Microsoft Agent Framework. "
        "This API provides endpoints for executing workflows, managing agents, and monitoring execution."
    ),
    version="0.6.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(
    ","
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors.

    Args:
        request: The request that caused the error
        exc: The validation error

    Returns:
        JSON response with error details
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "Validation error",
        extra={"request_id": request_id, "errors": exc.errors()},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "request_id": request_id,
        },
    )


@app.exception_handler(AgenticFleetAPIError)
async def agentic_fleet_exception_handler(
    request: Request, exc: AgenticFleetAPIError
) -> JSONResponse:
    """Handle custom Agentic Fleet API errors.

    Args:
        request: The request that caused the error
        exc: The custom exception

    Returns:
        JSON response with error details
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"API error: {exc.message}",
        extra={"request_id": request_id, "status_code": exc.status_code},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors.

    Args:
        request: The request that caused the error
        exc: The exception

    Returns:
        JSON response with error details
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        f"Unexpected error: {exc!s}",
        extra={"request_id": request_id},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "request_id": request_id,
        },
    )


# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["workflow"])


# Root endpoint
@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint redirecting to API documentation.

    Returns:
        Message with links to documentation
    """
    return {
        "message": "Agentic Fleet API",
        "version": "0.6.0",
        "docs": "/api/docs",
        "health": "/health",
    }
