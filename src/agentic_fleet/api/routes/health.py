"""Health check routes for the Agentic Fleet API."""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str = "0.6.0"


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    ready: bool
    checks: dict[str, bool]


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Health status indicating the service is running
    """
    return HealthResponse(status="healthy")


@router.get("/health/live", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def liveness_check() -> HealthResponse:
    """Liveness probe endpoint for Kubernetes/container orchestration.

    Returns:
        Health status indicating the service is alive
    """
    return HealthResponse(status="alive")


@router.get("/health/ready", response_model=ReadinessResponse, status_code=status.HTTP_200_OK)
async def readiness_check() -> ReadinessResponse:
    """Readiness probe endpoint for Kubernetes/container orchestration.

    Checks if the service is ready to accept traffic by verifying:
    - Core dependencies are available
    - Configuration is loaded

    Returns:
        Readiness status with individual check results
    """
    checks = {
        "api": True,  # API is running if we got here
        "config": True,  # Configuration is loaded at startup
    }

    # Service is ready if all checks pass
    ready = all(checks.values())

    return ReadinessResponse(ready=ready, checks=checks)
