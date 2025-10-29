from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, JSONResponse, WebSocket, WebSocketDisconnect, status

from agenticfleet.api.dependencies import get_backend, get_backend_from_websocket, get_optional_redis_client
from agenticfleet.api.models.chat_models import ChatRequest, ChatResponse, ExecutionState, ExecutionStatus
from agenticfleet.api.redis_client import RedisClient
from agenticfleet.api.services.workflow_executor import execute_workflow_background
from agenticfleet.api.state import BackendState

router = APIRouter(tags=["chat"])
LOGGER = logging.getLogger(__name__)


@router.post("/v1/chat", response_model=ChatResponse)
async def create_chat_execution(
    request: ChatRequest,
    state: BackendState = Depends(get_backend),
) -> ChatResponse:
    execution_id = str(uuid4())
    execution_state = ExecutionState(
        execution_id=execution_id,
        workflow_id=request.workflow_id,
        status=ExecutionStatus.PENDING,
        user_message=request.message,
        conversation_id=request.conversation_id,
        started_at=datetime.utcnow(),
        metadata=request.metadata,
    )

    if state.redis_client:
        try:
            await state.redis_client.save_state(execution_state)
        except Exception as exc:  # pragma: no cover - Redis is optional in tests
            LOGGER.warning("Failed to persist execution state: %s", exc)

    task = asyncio.create_task(
        execute_workflow_background(state, execution_id, request.workflow_id, request.message)
    )
    state.background_tasks.add(task)
    task.add_done_callback(state.background_tasks.discard)

    base_url = os.getenv("BASE_URL", "ws://localhost:8000")
    if base_url.startswith("http://"):
        base_url = base_url.replace("http://", "ws://")
    elif base_url.startswith("https://"):
        base_url = base_url.replace("https://", "wss://")
    websocket_url = f"{base_url}/ws/chat/{execution_id}"

    return ChatResponse(
        execution_id=execution_id,
        status=ExecutionStatus.PENDING,
        websocket_url=websocket_url,
        message="Execution created successfully",
    )


@router.get("/v1/chat/executions/{execution_id}")
async def get_execution_status(
    execution_id: str,
    redis_client: RedisClient | None = Depends(get_optional_redis_client),
) -> JSONResponse:
    if not redis_client:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Redis not available"},
        )

    try:
        state = await redis_client.get_state(execution_id)
        if not state:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Execution not found"},
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=state.to_status_response().model_dump(),
        )
    except Exception as exc:
        LOGGER.error("Failed to get execution status: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )


@router.websocket("/ws/chat/{execution_id}")
async def websocket_chat(
    websocket: WebSocket,
    execution_id: str,
    state: BackendState = Depends(get_backend_from_websocket),
) -> None:
    manager = state.websocket_manager
    await manager.connect(websocket, execution_id)

    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket, execution_id)
    except Exception as exc:  # pragma: no cover - defensive guard
        LOGGER.error("WebSocket error for %s: %s", execution_id, exc)
        manager.disconnect(websocket, execution_id)
