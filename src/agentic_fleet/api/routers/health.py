"""
Health check endpoints for the Agentic Fleet API.

Provides:
- /health: lightweight status (returns 200 + {"status": "ok"} when framework healthy,
           503 with details when unhealthy)
- /health/detailed: always 200, includes package version status (ok|degraded|error)

Framework health functions are synchronous (no await).
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi_limiter.depends import RateLimiter

from agentic_fleet.framework.health import (
    FrameworkHealthError,
    check_framework_health,
    verify_framework_health,
)

logger = logging.getLogger(__name__)

# Cache TTL placeholder (not yet used for in-memory caching here)
CACHE_TTL = 300


async def conditional_rate_limiter(request: Request) -> None:
    """Conditional rate limiter dependency that only applies if Redis is available.

    This function checks if Redis is available via app state. If Redis is available
    and FastAPILimiter is initialized, it applies rate limiting. Otherwise, it
    skips rate limiting gracefully.

    Args:
        request: FastAPI request object

    Returns:
        None (dependency injection)
    """
    # Check if Redis is available via app state
    redis_available = (
        hasattr(request.app.state, "redis_available") and request.app.state.redis_available
    )

    if redis_available:
        # Apply rate limiting if Redis is available
        # RateLimiter needs FastAPILimiter to be initialized
        try:
            # Check if FastAPILimiter is initialized by checking for redis attribute
            from fastapi_limiter import FastAPILimiter

            if hasattr(FastAPILimiter, "redis") and FastAPILimiter.redis is not None:
                limiter = RateLimiter(times=100, seconds=60)
                # RateLimiter is callable and expects the request
                await limiter(request)
        except (AttributeError, Exception) as e:
            # If rate limiting fails (e.g., FastAPILimiter not initialized),
            # log but don't block the request
            logger.debug(f"Rate limiting skipped (Redis unavailable or not initialized): {e}")
    # If Redis is not available, skip rate limiting (no-op)


router = APIRouter(
    tags=["system"],
    dependencies=[
        # Rate limiting: 100 requests per minute per IP (only if Redis is available)
        Depends(conditional_rate_limiter)
    ],
)


@router.get(  # type: ignore
    "/health",
    summary="Check system health",
    response_description="Current health status of the system",
    responses={
        200: {"description": "System is healthy"},
        429: {"description": "Too many requests"},
        503: {"description": "System is unhealthy"},
    },
)
async def health_check() -> dict[str, Any]:
    """Lightweight framework health check.

    Returns:
        {"status": "ok"} when healthy.

    Raises:
        HTTPException(503): When framework health fails.
    """
    try:
        # Synchronous verification; raises FrameworkHealthError if unhealthy
        verify_framework_health()
        return {"status": "ok"}

    except FrameworkHealthError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "message": "Framework health check failed",
                "details": e.health_status,
            },
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "message": f"Health check failed: {e!s}",
            },
        ) from e


@router.get(  # type: ignore
    "/health/detailed",
    summary="Get detailed health information",
    response_description="Detailed health status of the system",
    responses={
        200: {"description": "Detailed health information"},
        429: {"description": "Too many requests"},
        500: {"description": "Internal server error"},
    },
)
async def detailed_health_check() -> dict[str, Any]:
    """Detailed framework health including package versions.

    Returns:
        {
            "status": "ok" | "error",
            "framework": {
                "status": "ok" | "degraded" | "error",
                "packages": { ... }
            }
        }

    Notes:
        This endpoint always returns HTTP 200 unless an unexpected internal error occurs.
    """
    try:
        is_healthy, health_status = check_framework_health()
        return {
            "status": "ok" if is_healthy else "error",
            "framework": health_status,
        }
    except Exception as e:
        error_msg = f"Failed to get detailed health status: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": error_msg,
            },
        ) from e
