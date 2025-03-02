"""
API package for the Agentic Fleet application.

This package contains all the API-related code, including routes, middleware, and dependencies.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routes
from agentic_fleet.api.routes import agents, chat, tasks

# Create FastAPI app
app = FastAPI(
    title="Agentic Fleet API",
    description="API for the Agentic Fleet multi-agent system",
    version="0.4.90",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents, prefix="/api/agents", tags=["agents"])
app.include_router(tasks, prefix="/api/tasks", tags=["tasks"])
app.include_router(chat, prefix="/api/chat", tags=["chat"])

# Export app
__all__ = ["app"]
