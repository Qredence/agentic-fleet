"""FastAPI application for AgenticFleet HTTP API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agentic_fleet.utils.error_utils import create_user_facing_error, log_error_with_context

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="AgenticFleet API",
    description="DSPy-Enhanced Multi-Agent Orchestration API",
    version="0.6.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning API information."""
    return {
        "name": "AgenticFleet API",
        "version": "0.6.0",
        "status": "running",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/v1/info")
async def api_info() -> dict[str, Any]:
    """API information endpoint."""
    return {
        "name": "AgenticFleet",
        "version": "0.6.0",
        "description": "DSPy-Enhanced Multi-Agent Orchestration System",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
        },
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler that sanitizes error messages."""
    error_response = create_user_facing_error(exc, error_code="INTERNAL_ERROR")
    log_error_with_context(exc, context={"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=500,
        content=error_response,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with sanitized messages."""
    error_response = create_user_facing_error(exc, error_code=str(exc.status_code))
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
    )


__all__ = ["app"]
