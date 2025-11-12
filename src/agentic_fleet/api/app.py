from __future__ import annotations

import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_limiter import FastAPILimiter
from starlette.middleware.base import BaseHTTPMiddleware

from agentic_fleet.api.approvals.routes import router as approvals_router
from agentic_fleet.api.chat.routes import router as chat_router
from agentic_fleet.api.conversations.routes import router as conversations_router
from agentic_fleet.api.entities.routes import router as entities_router
from agentic_fleet.api.exceptions import register_exception_handlers
from agentic_fleet.api.responses.routes import router as responses_router
from agentic_fleet.api.workflows.routes import router as workflows_router
from agentic_fleet.framework.health import verify_framework_health
from agentic_fleet.utils.logging import setup_logging
from agentic_fleet.utils.performance import clear_correlation_id, set_correlation_id
from agentic_fleet.utils.redis_cache import RedisCacheManager

logger = logging.getLogger(__name__)


def is_redis_enabled() -> bool:
    """Check if Redis is enabled via environment variable.

    Returns:
        True if REDIS_ENABLED is set to 'true' (case-insensitive), False otherwise.
        Defaults to True for backward compatibility.
    """
    redis_enabled = os.getenv("REDIS_ENABLED", "true").lower()
    return redis_enabled in ("true", "1", "yes", "on")


async def check_redis_availability(redis_url: str) -> tuple[bool, str]:
    """Check if Redis is available at the given URL.

    Args:
        redis_url: Redis connection URL

    Returns:
        Tuple of (is_available, status_message)
    """
    try:
        redis_client = aioredis.from_url(
            redis_url,
            encoding="utf8",
            decode_responses=True,
        )
        await redis_client.ping()
        await redis_client.close()
        return True, "ok"
    except Exception as e:
        return False, f"error: {e!s}"


class CorrelationMiddleware(BaseHTTPMiddleware):  # type: ignore
    """Middleware to add correlation ID to requests and responses."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process the request and add correlation ID to the response.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler in the chain

        Returns:
            The response with correlation ID header added
        """
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(correlation_id)

        try:
            # Process the request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response
        finally:
            # Clear correlation ID from context
            clear_correlation_id()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events.

    This context manager handles:
    - Initialization of Redis connection for caching and rate limiting (if enabled)
    - Framework health checks on startup
    - Cleanup on shutdown
    """
    redis_enabled = is_redis_enabled()
    cache_manager: RedisCacheManager | None = None
    redis_available = False

    # Initialize Redis only if enabled
    if redis_enabled:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            cache_manager = RedisCacheManager(redis_url)
            redis_client = cache_manager.async_client

            # Try to initialize rate limiter with async Redis client
            await FastAPILimiter.init(redis_client)
            redis_available = True
            logger.info("Redis initialized successfully for caching and rate limiting")
        except Exception as e:
            logger.warning(
                f"Redis initialization failed (rate limiting and caching disabled): {e!s}. "
                "Application will continue without Redis features."
            )
            # Clean up partial initialization
            if cache_manager:
                with suppress(Exception):
                    await cache_manager.close()
                cache_manager = None
    else:
        logger.info("Redis is disabled via REDIS_ENABLED environment variable")

    # Store Redis availability state in app state for use by other components
    app.state.redis_enabled = redis_enabled
    app.state.redis_available = redis_available

    # Verify framework health
    try:
        verify_framework_health()
        logger.info("Framework health check passed on startup")
    except Exception as e:
        logger.critical(f"Critical: Framework health check failed on startup: {e}")

    yield

    # Shutdown - only close Redis connections if they were initialized
    if redis_available and cache_manager:
        try:
            await FastAPILimiter.close()
            await cache_manager.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connections: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    This function sets up the FastAPI application with:
    - CORS middleware for cross-origin requests
    - Request/response logging middleware
    - Exception handlers
    - API routes
    - Caching and rate limiting
    - Static file serving

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    # Configure logging before creating app
    setup_logging()
    logger.info("Starting AgenticFleet API")

    app = FastAPI(
        title="AgenticFleet API",
        description="Agentic Fleet API for multi-agent orchestration",
        version="1.0.0",
        contact={
            "name": "AgenticFleet Support",
            "url": "https://github.com/Qredence/agentic-fleet/issues",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add correlation middleware first (processes requests before CORS)
    app.add_middleware(CorrelationMiddleware)

    # Add CORS middleware with secure defaults
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000,http://localhost:5173"
        ).split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Add explicit OPTIONS handlers to resolve preflight 400 responses
    @app.options("/{path:path}")  # type: ignore
    async def preflight_handler(path: str) -> dict[str, str]:
        """Handle CORS preflight requests."""
        return {"status": "ok"}

    @app.get("/health")  # type: ignore
    async def health_check() -> dict[str, str]:
        """Basic health check endpoint.

        Returns:
            dict: Status of the service and Redis connection
        """
        redis_enabled = is_redis_enabled()
        rate_limiting_status = "disabled"

        if redis_enabled:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            redis_available, redis_status = await check_redis_availability(redis_url)

            # Check app state if available (set during lifespan)
            if hasattr(app.state, "redis_available"):
                redis_available = app.state.redis_available

            rate_limiting_status = "enabled" if redis_available else "disabled (Redis unavailable)"
        else:
            redis_status = "disabled (REDIS_ENABLED=false)"

        return {
            "status": "ok",
            "redis": redis_status,
            "version": "0.5.5",
            "rate_limiting": rate_limiting_status,
        }

    # Register all routers - maintain backward compatibility with existing endpoints
    # Include health check endpoints from routers/health.py
    from agentic_fleet.api.routers import api_router as system_health_router

    app.include_router(system_health_router, tags=["system"])
    app.include_router(conversations_router, prefix="/v1")
    app.include_router(chat_router, prefix="/v1")
    app.include_router(workflows_router, prefix="/v1")
    app.include_router(approvals_router, prefix="/v1")

    # Register new OpenAI-compatible endpoints
    app.include_router(entities_router, prefix="/v1")
    app.include_router(responses_router, prefix="/v1")

    # Register centralized exception handlers
    register_exception_handlers(app)

    # Mount static files for production builds (UI directory)
    # Only mount if UI directory exists and we're in production mode
    ui_dir = Path(__file__).parent.parent / "ui"

    if ui_dir.exists() and ui_dir.is_dir():
        # Mount static files at root for SPA routing
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app


# Create app instance for direct import
app = create_app()
