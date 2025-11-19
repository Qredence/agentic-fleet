from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agentic_fleet.api.middlewares import LoggingMiddleware, RequestIDMiddleware
from agentic_fleet.api.routes import health, workflow
from agentic_fleet.core.config import settings
from agentic_fleet.core.exceptions import generic_exception_handler, http_exception_handler
from agentic_fleet.db.base_class import Base
from agentic_fleet.db.cosmos import cosmos_db
from agentic_fleet.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not settings.AGENTICFLEET_USE_COSMOS:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
    else:
        await cosmos_db.connect()

    yield

    # Shutdown
    if settings.AGENTICFLEET_USE_COSMOS:
        await cosmos_db.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev, or restrict based on settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)

# Exception Handlers
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore
app.add_exception_handler(Exception, generic_exception_handler)

# Routes
app.include_router(health.router, tags=["health"])
app.include_router(workflow.router, prefix=f"{settings.API_V1_STR}/workflow", tags=["workflow"])


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Agentic Fleet API",
        "version": "0.6.0",
        "docs": "/api/docs",
        "health": "/health",
    }
