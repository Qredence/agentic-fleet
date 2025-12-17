"""Chat streaming routes.

Provides both WebSocket and SSE endpoints for chat streaming.
SSE is the recommended approach for new integrations due to:
- Built-in browser auto-reconnect
- Works through all proxies/CDNs
- Simpler error handling
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request, WebSocket
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


# --------------------------------------------------------------------------
# Request/Response Models
# --------------------------------------------------------------------------


class HITLResponseRequest(BaseModel):
    """Human-in-the-loop response payload."""

    request_id: str
    response: dict[str, Any]


class CancelResponse(BaseModel):
    """Cancel operation response."""

    status: str
    workflow_id: str


class HITLResponse(BaseModel):
    """HITL submission response."""

    status: str
    request_id: str


# --------------------------------------------------------------------------
# SSE Streaming Endpoints (Recommended)
# --------------------------------------------------------------------------


@router.get("/chat/{conversation_id}/stream")
async def stream_chat_sse(
    request: Request,
    conversation_id: str,
    message: str = Query(..., description="User message to send"),
    reasoning_effort: str | None = Query(
        None, description="Reasoning effort level: minimal, medium, maximal"
    ),
    enable_checkpointing: bool = Query(False, description="Enable workflow checkpointing"),
) -> StreamingResponse:
    """Stream chat responses via Server-Sent Events (SSE).

    This endpoint streams workflow events as SSE, which provides:
    - Automatic browser reconnection on connection loss
    - Standard HTTP semantics (works with all proxies)
    - Simple integration with EventSource API

    Event format:
        data: {"type": "response.delta", "delta": "Hello", ...}

    Stream ends with:
        data: {"type": "done", ...}

    Args:
        conversation_id: Unique conversation identifier
        message: The user's message
        reasoning_effort: Optional reasoning level (minimal/medium/maximal)
        enable_checkpointing: Whether to enable workflow checkpointing

    Returns:
        StreamingResponse with text/event-stream content type
    """
    # Lazy imports to avoid circular dependencies
    from agentic_fleet.services.chat_sse import ChatSSEService
    from agentic_fleet.utils.cfg import load_config
    from agentic_fleet.workflows.config import build_workflow_config_from_yaml
    from agentic_fleet.workflows.supervisor import create_supervisor_workflow

    app = request.app
    session_manager = getattr(app.state, "session_manager", None)
    conversation_manager = getattr(app.state, "conversation_manager", None)

    if session_manager is None or conversation_manager is None:
        raise HTTPException(status_code=503, detail="Server not initialized")

    # Get or create shared workflow (same pattern as WebSocket)
    workflow = getattr(app.state, "supervisor_workflow", None)
    if workflow is None:
        yaml_config = getattr(app.state, "yaml_config", None)
        if yaml_config is None:
            yaml_config = load_config(validate=False)

        workflow_config = build_workflow_config_from_yaml(
            yaml_config,
            compile_dspy=False,
        )

        workflow = await create_supervisor_workflow(
            compile_dspy=False,
            config=workflow_config,
            dspy_routing_module=getattr(app.state, "dspy_routing_module", None),
            dspy_quality_module=getattr(app.state, "dspy_quality_module", None),
            dspy_tool_planning_module=getattr(app.state, "dspy_tool_planning_module", None),
        )
        app.state.supervisor_workflow = workflow

    # Get or create SSE service (cached per app for cancel/response tracking)
    sse_service = getattr(app.state, "sse_service", None)
    if sse_service is None:
        sse_service = ChatSSEService(
            workflow=workflow,
            session_manager=session_manager,
            conversation_manager=conversation_manager,
        )
        app.state.sse_service = sse_service

    return StreamingResponse(
        sse_service.stream_chat(
            conversation_id=conversation_id,
            message=message,
            reasoning_effort=reasoning_effort,
            enable_checkpointing=enable_checkpointing,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/chat/{conversation_id}/respond")
async def submit_hitl_response(
    request: Request,
    conversation_id: str,  # noqa: ARG001 - part of REST path
    workflow_id: str = Query(..., description="Active workflow ID"),
    body: HITLResponseRequest = Body(...),  # noqa: B008
) -> HITLResponse:
    """Submit a human-in-the-loop response.

    When the workflow emits a request event (e.g., approval needed),
    use this endpoint to submit the user's response.

    Args:
        conversation_id: Conversation identifier
        workflow_id: The workflow ID from the SSE stream
        body: Response payload with request_id and response data

    Returns:
        Confirmation of response submission
    """
    app = request.app
    sse_service = getattr(app.state, "sse_service", None)

    if sse_service is None:
        raise HTTPException(status_code=503, detail="No active SSE service")

    success = await sse_service.submit_response(
        workflow_id=workflow_id,
        request_id=body.request_id,
        response=body.response,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found or already completed")

    return HITLResponse(status="ok", request_id=body.request_id)


@router.post("/chat/{conversation_id}/cancel")
async def cancel_stream(
    request: Request,
    conversation_id: str,  # noqa: ARG001 - part of REST path
    workflow_id: str = Query(..., description="Workflow ID to cancel"),
) -> CancelResponse:
    """Cancel an active SSE stream.

    Args:
        conversation_id: Conversation identifier
        workflow_id: The workflow ID to cancel

    Returns:
        Confirmation of cancellation
    """
    app = request.app
    sse_service = getattr(app.state, "sse_service", None)

    if sse_service is None:
        raise HTTPException(status_code=503, detail="No active SSE service")

    success = await sse_service.cancel_stream(workflow_id)

    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found or already completed")

    return CancelResponse(status="cancelled", workflow_id=workflow_id)


# --------------------------------------------------------------------------
# WebSocket Endpoint (Legacy - kept for backward compatibility)
# --------------------------------------------------------------------------


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming chat responses.

    Note: SSE endpoints are recommended for new integrations.
    This WebSocket endpoint is maintained for backward compatibility.
    """
    # Lazy import to avoid circular dependency with api.events
    from agentic_fleet.services.chat_websocket import ChatWebSocketService

    service = ChatWebSocketService()
    await service.handle(websocket)


__all__ = ["router"]
