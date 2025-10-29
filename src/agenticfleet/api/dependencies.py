from __future__ import annotations

from fastapi import Depends, Request, WebSocket

from agenticfleet.api.redis_client import RedisClient
from agenticfleet.api.state import BackendState, get_backend_state


def get_backend(request: Request) -> BackendState:
    """FastAPI dependency that exposes the shared :class:`BackendState`."""

    return get_backend_state(request)


def get_backend_from_websocket(websocket: WebSocket) -> BackendState:
    """WebSocket dependency for accessing the shared backend state."""

    return get_backend_state(websocket)


def get_redis_client(state: BackendState = Depends(get_backend)) -> RedisClient:
    """Return the active Redis client or raise if unavailable."""

    client = state.redis_client
    if client is None:
        raise RuntimeError("Redis client not initialised")
    return client


def get_optional_redis_client(
    state: BackendState = Depends(get_backend),
) -> RedisClient | None:
    """Return the active Redis client if the connection succeeded."""

    return state.redis_client
