"""Chat streaming routes.

Thin WebSocket route definitions that delegate implementation details to the
services layer.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from agentic_fleet.services.chat_websocket import ChatWebSocketService

router = APIRouter()
_service = ChatWebSocketService()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming chat responses."""
    await _service.handle(websocket)


__all__ = ["router"]
