"""Main FastAPI application for Agentic Fleet."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agentic_fleet.api.db.base_class import Base
from agentic_fleet.api.db.cosmos import cosmos_db
from agentic_fleet.api.db.session import engine
from agentic_fleet.api.exceptions import AgenticFleetAPIError
from agentic_fleet.api.middlewares import LoggingMiddleware, RequestIDMiddleware
from agentic_fleet.api.routes import health, history, logs, workflow
from agentic_fleet.api.settings import settings
from agentic_fleet.utils.logger import setup_logger

# Setup logging with file output for /logs endpoint
logger = setup_logger(__name__, log_file=settings.LOG_FILE_PATH)

API_PREFIX = "/api"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    logger.info(f"Starting {settings.PROJECT_NAME}")

    if not settings.AGENTICFLEET_USE_COSMOS:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        await cosmos_db.connect()

    yield

    if settings.AGENTICFLEET_USE_COSMOS:
        await cosmos_db.close()


# Create FastAPI application
app = FastAPI(
    title="Agentic Fleet",
    description="API for Agentic Fleet",
    version="0.6.2",
    openapi_version="3.0.2",
    # Routes are explicitly prefixed with API_PREFIX; keep server url root to avoid double-prefixing
    servers=[{"url": "/"}],
    lifespan=lifespan,
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["*"],  # Simplified for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middlewares
app.add_middleware(LoggingMiddleware)  # type: ignore[arg-type]
app.add_middleware(RequestIDMiddleware)  # type: ignore[arg-type]


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(AgenticFleetAPIError)
async def agentic_fleet_exception_handler(
    request: Request, exc: AgenticFleetAPIError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"API Error: {exc.message}", extra={"request_id": request_id})
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unexpected error: {exc}", extra={"request_id": request_id})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"},
    )


# Include routers
app.include_router(health.router, prefix=API_PREFIX, tags=["Health"])
app.include_router(workflow.router, prefix=f"{API_PREFIX}/workflows", tags=["Workflows"])
app.include_router(history.router, prefix=f"{API_PREFIX}/history", tags=["History"])
app.include_router(logs.router, prefix=f"{API_PREFIX}/logs", tags=["Logs"])
