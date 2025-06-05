"""
Main FastAPI application with comprehensive OpenAPI documentation.

This module provides the main FastAPI application that includes all routes
and proper OpenAPI documentation configuration.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_fleet.api.middleware import LoggingMiddleware
from agentic_fleet.api.routes import agents, chat, tasks
from agentic_fleet.database.session import get_db
from agentic_fleet.exceptions import AgenticFleetAPIError, AgenticFleetDatabaseError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agentic_fleet")

# Extracted FastAPI description
FASTAPI_DESCRIPTION = """
## Agentic Fleet API

A powerful multi-agent system for adaptive AI reasoning and automation.

### Features

* **Agent Management**: Create, update, and manage AI agents
* **Task Management**: Assign and track tasks across agents
* **Real-time Chat**: WebSocket-based chat interface
* **Multi-model Support**: Support for various AI models and providers

### Getting Started

1. **Explore the API**: Use the interactive documentation below to explore available endpoints
2. **Create an Agent**: Start by creating an AI agent using the `/agents` endpoint
3. **Create a Task**: Create tasks and assign them to agents using the `/tasks` endpoint
4. **Chat Interface**: Use the WebSocket endpoint at `/chat/ws` for real-time communication

### Authentication

Currently, the API is open for development. Authentication will be added in future versions.

### Rate Limiting

No rate limiting is currently implemented.

### Support

For issues and support, please visit our [GitHub repository](https://github.com/Qredence/AgenticFleet).
"""
app = FastAPI(
    title="Agentic Fleet API",
    description=FASTAPI_DESCRIPTION,
    version="0.1.0",
    contact={
        "name": "Qredence",
        "url": "https://github.com/Qredence/AgenticFleet",
        "email": "contact@qredence.ai",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and system status endpoints.",
        },
        {
            "name": "agents",
            "description": "Operations with AI agents. Create, read, update, and delete agents.",
        },
        {
            "name": "tasks",
            "description": "Task management operations. Create and assign tasks to agents.",
        },
        {
            "name": "chat",
            "description": "Real-time chat operations. Send messages and manage chat sessions.",
        },
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)

# Exception handlers


@app.exception_handler(AgenticFleetAPIError)
async def api_exception_handler(request: Request, exc: AgenticFleetAPIError) -> JSONResponse:
    """
    Handle API exceptions.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(AgenticFleetDatabaseError)
async def database_exception_handler(request: Request, exc: AgenticFleetDatabaseError) -> JSONResponse:
    """
    Handle database exceptions.
    """
    logger.error(f"Database error: {exc.message}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(agents, prefix="/agents", tags=["agents"])
app.include_router(tasks, prefix="/tasks", tags=["tasks"])
app.include_router(chat, prefix="/chat", tags=["chat"])


@app.get("/", tags=["health"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint that returns API information.
    
    Returns basic information about the API including name, version, and description.
    This endpoint can be used to verify that the API is running and provides
    links to the interactive documentation.
    
    Returns:
        Dict containing API information and documentation links
    """
    return {
        "name": "Agentic Fleet API",
        "version": app.version,
        "description": "A powerful multi-agent system for adaptive AI reasoning and automation",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "status": "running",
        "features": [
            "Agent Management",
            "Task Management", 
            "Real-time Chat",
            "Multi-model Support"
        ]
    }


@app.get("/health", tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint.

    Checks if the database connection is working and returns system information.
    This endpoint is useful for monitoring and ensuring the API is functioning properly.
    
    Returns:
        Dict containing health status and system information
    """
    # Check database connection
    try:
        # Try to execute a simple query to check database connection
        await db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "disconnected"

    # Get system information
    system_info = {
        "python_version": sys.version,
        "time": datetime.now().isoformat(),
    }

    # Get environment information
    env = os.environ.get("ENVIRONMENT", "development")

    return {
        "status": "healthy",
        "database": db_status,
        "environment": env,
        "system": system_info,
        "api_version": app.version,
    }


@app.get("/api", include_in_schema=False)
async def redirect_to_docs():
    """Redirect /api to /docs for convenience."""
    return RedirectResponse(url="/docs")


@app.get("/documentation", include_in_schema=False)
async def redirect_to_docs_alt():
    """Redirect /documentation to /docs for convenience."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment variables
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "False").lower() == "true"

    logger.info(f"Starting Agentic Fleet API on {host}:{port}")
    logger.info(f"OpenAPI documentation available at http://{host}:{port}/docs")
    logger.info(f"ReDoc documentation available at http://{host}:{port}/redoc")

    # Run the application
    uvicorn.run(
        "agentic_fleet.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )