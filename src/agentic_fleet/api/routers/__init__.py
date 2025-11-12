"""API routers for the Agentic Fleet application."""

from fastapi import APIRouter

from agentic_fleet.api.routers import health

# Create a router for all API endpoints
api_router = APIRouter(prefix="/v1")

# Include all routers
api_router.include_router(health.router, prefix="/system", tags=["system"])
