"""API router aggregation.

Aggregates all route modules into a single router for clean registration
in the main FastAPI application.
"""

from fastapi import APIRouter

from agentic_fleet.api.api_v1.api import api_router as api_v1_router

api_router = APIRouter()

# Include versioned API routes (mounted by the main app under /api/v1)
api_router.include_router(api_v1_router)
