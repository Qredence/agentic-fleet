from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agenticfleet import __version__
from agenticfleet.api.redis_client import RedisClient
from agenticfleet.api.routes import register_routes
from agenticfleet.api.state import BackendState, get_backend_state
from agenticfleet.persistance.database import init_db

LOGGER = logging.getLogger(__name__)


def create_app() -> FastAPI:
    state = BackendState()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        init_db()
        LOGGER.info("Database initialised")

        app.state.backend = state
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        state.redis_client = RedisClient(redis_url=redis_url, ttl_seconds=3600)

        try:
            await state.redis_client.connect()
            LOGGER.info("Redis client connected")
        except Exception as exc:
            LOGGER.error("Failed to connect to Redis: %s", exc)
            state.redis_client = None

        try:
            yield
        finally:
            backend_state = get_backend_state(app)
            if backend_state.redis_client:
                try:
                    await backend_state.redis_client.disconnect()
                    LOGGER.info("Redis client disconnected")
                except Exception:
                    LOGGER.exception("Error while disconnecting Redis client")

            while backend_state.background_tasks:
                task = backend_state.background_tasks.pop()
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:  # pragma: no cover - shutdown guard
                    pass

    app = FastAPI(title="AgenticFleet Minimal API", version=__version__, lifespan=lifespan)
    app.state.backend = state

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_routes(app)

    return app


app = create_app()
