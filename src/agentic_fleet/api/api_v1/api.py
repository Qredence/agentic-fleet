"""API v1 router aggregation.

This module mirrors the FastAPI full-stack template pattern:
- `api/api_v1/api.py` aggregates versioned routers
- `api/main.py` exposes the top-level `api_router`
"""

from fastapi import APIRouter

from agentic_fleet.api.routes import (
    agents,
    conversations,
    dspy,
    history,
    nlu,
    optimize,
    sessions,
    workflows,
)

api_router = APIRouter()

api_router.include_router(workflows.router, tags=["workflows"])
api_router.include_router(agents.router, tags=["agents"])
api_router.include_router(conversations.router, tags=["conversations"])
api_router.include_router(history.router, tags=["history"])
api_router.include_router(sessions.router, tags=["sessions"])
api_router.include_router(dspy.router, tags=["dspy"])
api_router.include_router(nlu.router, tags=["nlu"])
api_router.include_router(optimize.router, tags=["optimization"])

__all__ = ["api_router"]
