"""Main FastAPI application for Agentic Fleet."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentic_fleet.api.routes import workflow

app = FastAPI(
    title="Agentic Fleet API",
    description="API for orchestrating autonomous agents with DSPy and Microsoft Agent Framework.",
    version="0.5.0",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflow.router, prefix="/workflow", tags=["workflow"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
