from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import no_type_check

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from agentic_fleet.api.approvals.routes import router as approvals_router
from agentic_fleet.api.chat.routes import router as chat_router
from agentic_fleet.api.conversations.routes import router as conversations_router
from agentic_fleet.api.entities.routes import router as entities_router
from agentic_fleet.api.responses.routes import router as responses_router
from agentic_fleet.api.system.routes import router as system_router
from agentic_fleet.api.workflows.routes import router as workflows_router
from agentic_fleet.utils.logging import setup_logging
from agentic_fleet.utils.performance import clear_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)


class CorrelationMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """Middleware to inject correlation IDs into all requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with correlation ID."""
        # Generate unique correlation ID for this request
        correlation_id = str(uuid.uuid4())

        # Set correlation ID in context
        set_correlation_id(correlation_id)

        # Add to request state for logging
        request.state.correlation_id = correlation_id

        try:
            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response
        finally:
            # Clear correlation ID from context
            clear_correlation_id()


def create_app() -> FastAPI:
    """Create FastAPI application with all routes configured."""
    # Configure logging before creating app
    setup_logging()

    app = FastAPI(title="AgenticFleet API")

    # Add correlation middleware first (processes requests before CORS)
    app.add_middleware(CorrelationMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Add explicit OPTIONS handlers to resolve preflight 400 responses
    @no_type_check
    @app.options("/{path:path}")
    async def preflight_handler(path: str) -> dict[str, str]:
        """Handle CORS preflight requests."""
        return {"status": "ok"}

    # Register all routers - maintain backward compatibility with existing endpoints
    app.include_router(system_router, prefix="/v1/system")
    # Also expose health endpoint at /v1/health for convenience
    app.include_router(system_router, prefix="/v1", tags=["health"])
    app.include_router(conversations_router, prefix="/v1")
    app.include_router(chat_router, prefix="/v1")
    app.include_router(workflows_router, prefix="/v1")
    app.include_router(approvals_router, prefix="/v1")

    # Register new OpenAI-compatible endpoints
    app.include_router(entities_router, prefix="/v1")
    app.include_router(responses_router, prefix="/v1")

    # Mount static files for production builds (UI directory)
    # Only mount if UI directory exists and we're in production mode
    ui_dir = Path(__file__).parent.parent / "ui"

    if ui_dir.exists() and ui_dir.is_dir():
        # Mount static files at root for SPA routing
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app


# Create app instance for direct import
app = create_app()
