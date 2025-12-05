"""Custom FastAPI middlewares for the AgenticFleet API."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to each response and request state.

    - Reuses incoming ``X-Request-ID`` if provided, otherwise generates a UUID4.
    - Adds the ID back on the response for traceability.
    """

    header_name = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and attach X-Request-ID header."""
        request_id = request.headers.get(self.header_name) or uuid.uuid4().hex
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response


__all__ = ["RequestIDMiddleware"]
