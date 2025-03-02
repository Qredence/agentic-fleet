"""
Routes package for the Agentic Fleet API.

This package contains all the route modules for the API.
"""

from agentic_fleet.api.routes.agents import router as agents_router
from agentic_fleet.api.routes.chat import router as chat_router
from agentic_fleet.api.routes.tasks import router as tasks_router

# Export the routers
agents = agents_router
tasks = tasks_router
chat = chat_router

__all__ = ["agents", "tasks", "chat"]
