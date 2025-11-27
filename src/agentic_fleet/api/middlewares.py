"""Custom middleware for the Agentic Fleet API."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request IDs to all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request state and response headers.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response with X-Request-ID header
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response from the route handler
        """
        request_id = getattr(request.state, "request_id", "unknown")
        start_time = time.time()

        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            },
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )

        return response


class ChatMiddleware:
    """Base class for chat middlewares.

    Allows interception of chat workflow lifecycle events.
    """

    async def on_start(self, task: str, context: dict[str, Any]) -> None:
        """Called when a chat workflow starts."""
        pass

    async def on_event(self, event: Any) -> None:
        """Called when a workflow event occurs."""
        pass

    async def on_end(self, result: Any) -> None:
        """Called when a chat workflow completes successfully."""
        pass

    async def on_error(self, error: Exception) -> None:
        """Called when a chat workflow fails."""
        pass
