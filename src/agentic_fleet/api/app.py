from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentic_fleet.api.approvals.routes import router as approvals_router
from agentic_fleet.api.chat.routes import router as chat_router
from agentic_fleet.api.conversations.routes import router as conversations_router
from agentic_fleet.api.system.routes import router as system_router
from agentic_fleet.api.workflows.routes import router as workflows_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Sets up the AgenticFleet API with CORS middleware and all route handlers
    for conversations, chat, workflows, approvals, and system endpoints.
    
    Returns:
        FastAPI: Configured FastAPI application instance
        
    Example:
        >>> app = create_app()
        >>> # Run with: uvicorn agentic_fleet.server:app
    """
    app = FastAPI(title="AgenticFleet API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(system_router, prefix="/v1")
    app.include_router(conversations_router, prefix="/v1")
    app.include_router(chat_router, prefix="/v1")
    app.include_router(workflows_router, prefix="/v1")
    app.include_router(approvals_router, prefix="/v1")

    return app
