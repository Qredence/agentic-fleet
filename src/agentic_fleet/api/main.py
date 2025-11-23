"""Main FastAPI application for Agentic Fleet."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware import _MiddlewareFactory
from starlette.middleware.cors import CORSMiddleware

from agentic_fleet.api.db.base_class import Base
from agentic_fleet.api.db.cosmos import cosmos_db
from agentic_fleet.api.db.session import engine
from agentic_fleet.api.exceptions import AgenticFleetAPIError
from agentic_fleet.api.middlewares import LoggingMiddleware, RequestIDMiddleware
from agentic_fleet.api.routes import chat, health, history, logs, optimization, workflow
from agentic_fleet.api.settings import settings
from agentic_fleet.utils.logger import setup_logger

setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle (startup/shutdown)."""
    # Initialize databases
    if not settings.AGENTICFLEET_USE_COSMOS:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield
    else:
        await cosmos_db.connect()

        try:
            yield
        finally:
            await cosmos_db.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

MiddlewareFactory = _MiddlewareFactory[Any]

# CORS
cors_middleware = cast(MiddlewareFactory, CORSMiddleware)
app.add_middleware(
    cors_middleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middlewares
app.add_middleware(cast(MiddlewareFactory, LoggingMiddleware))
app.add_middleware(cast(MiddlewareFactory, RequestIDMiddleware))

# Instrumentator
Instrumentator().instrument(app).expose(app)

# API Prefix
API_PREFIX = "/api"

# Include routers
app.include_router(health.router, prefix=API_PREFIX, tags=["Health"])
app.include_router(workflow.router, prefix=f"{API_PREFIX}/workflows", tags=["Workflows"])
app.include_router(history.router, prefix=f"{API_PREFIX}/history", tags=["History"])
app.include_router(logs.router, prefix=f"{API_PREFIX}/logs", tags=["Logs"])
app.include_router(optimization.router, prefix=f"{API_PREFIX}/optimization", tags=["Optimization"])
app.include_router(chat.router, prefix=API_PREFIX, tags=["Chat"])


@app.exception_handler(AgenticFleetAPIError)
async def api_error_handler(request: Request, exc: AgenticFleetAPIError):
    """Handle custom API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
