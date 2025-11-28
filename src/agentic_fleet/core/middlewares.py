"""Middleware definitions for the agentic fleet core."""

from typing import Any


class ChatMiddleware:
    """Base class for chat middlewares."""

    async def on_start(self, task: str, context: dict[str, Any]) -> None:
        """Called when a chat task starts."""
        pass

    async def on_event(self, event: Any) -> None:
        """Called when an event occurs during execution."""
        pass

    async def on_end(self, result: Any) -> None:
        """Called when a chat task completes successfully."""
        pass

    async def on_error(self, error: Exception) -> None:
        """Called when a chat task fails."""
        pass
