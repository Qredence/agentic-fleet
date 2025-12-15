"""Chat streaming routes.

Thin WebSocket route definitions that delegate implementation details to the
services layer.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming chat responses."""
    # Lazy import to avoid circular dependency with api.events
    from agentic_fleet.services.chat_websocket import ChatWebSocketService

    service = ChatWebSocketService()
    await service.handle(websocket)


__all__ = ["router"]
