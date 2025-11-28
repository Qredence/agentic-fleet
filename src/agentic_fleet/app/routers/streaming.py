"""Streaming chat endpoint using Server-Sent Events (SSE).

This module provides the streaming chat endpoint that converts
workflow events to SSE format for real-time frontend updates.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from agent_framework._workflows import (
    ExecutorCompletedEvent,
    MagenticAgentMessageEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
    WorkflowStatusEvent,
)
from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from agentic_fleet.app.dependencies import SessionManagerDep, WorkflowDep
from agentic_fleet.app.schemas import (
    ChatRequest,
    StreamEvent,
    StreamEventType,
    WorkflowSession,
    WorkflowStatus,
)
from agentic_fleet.utils.logger import setup_logger
from agentic_fleet.workflows.execution.streaming_events import ReasoningStreamEvent
from agentic_fleet.workflows.messages import (
    AnalysisMessage,
    ProgressMessage,
    QualityMessage,
    RoutingMessage,
)

if TYPE_CHECKING:
    from agentic_fleet.workflows.supervisor import WorkflowEvent

logger = setup_logger(__name__)

router = APIRouter()


# =============================================================================
# Real-time Logging Utilities
# =============================================================================


def _log_stream_event(event: StreamEvent, workflow_id: str) -> None:
    """Log a stream event to the console in real-time.

    Args:
        event: The stream event to log.
        workflow_id: The workflow ID for context.
    """
    event_type = event.type.value
    short_id = workflow_id[-8:] if len(workflow_id) > 8 else workflow_id

    if event.type == StreamEventType.ORCHESTRATOR_MESSAGE:
        logger.info(f"[{short_id}] 📢 {event.message}")
    elif event.type == StreamEventType.ORCHESTRATOR_THOUGHT:
        logger.info(f"[{short_id}] 💭 {event.kind}: {event.message}")
    elif event.type == StreamEventType.RESPONSE_DELTA:
        # Only log first 80 chars of deltas to avoid flooding
        delta_preview = (event.delta or "")[:80]
        if delta_preview:
            logger.debug(f"[{short_id}] ✏️  delta: {delta_preview}...")
    elif event.type == StreamEventType.RESPONSE_COMPLETED:
        result_preview = (event.message or "")[:100]
        logger.info(f"[{short_id}] ✅ Response: {result_preview}...")
    elif event.type == StreamEventType.REASONING_DELTA:
        # Log reasoning at debug level to avoid noise
        logger.debug(f"[{short_id}] 🧠 reasoning delta")
    elif event.type == StreamEventType.REASONING_COMPLETED:
        logger.info(f"[{short_id}] 🧠 Reasoning complete")
    elif event.type == StreamEventType.ERROR:
        logger.error(f"[{short_id}] ❌ Error: {event.error}")
    elif event.type == StreamEventType.AGENT_START:
        logger.info(f"[{short_id}] 🤖 Agent started: {event.agent_id}")
    elif event.type == StreamEventType.AGENT_COMPLETE:
        logger.info(f"[{short_id}] 🤖 Agent complete: {event.agent_id}")
    else:
        logger.debug(f"[{short_id}] {event_type}")


# =============================================================================
# Event Mapping Utilities
# =============================================================================


def _map_workflow_event(
    event: WorkflowEvent,
    accumulated_reasoning: str,
) -> tuple[StreamEvent | None, str]:
    """Map a workflow event to a StreamEvent for SSE.

    Args:
        event: The workflow event to map.
        accumulated_reasoning: Running total of reasoning text for partial error handling.

    Returns:
        Tuple of (StreamEvent or None, updated accumulated_reasoning).
    """
    if isinstance(event, WorkflowStartedEvent):
        return (
            StreamEvent(
                type=StreamEventType.ORCHESTRATOR_MESSAGE,
                message="Workflow started",
            ),
            accumulated_reasoning,
        )

    if isinstance(event, WorkflowStatusEvent):
        status_msg = f"Workflow status: {event.state.value}" if event.state else "Status update"
        return (
            StreamEvent(
                type=StreamEventType.ORCHESTRATOR_MESSAGE,
                message=status_msg,
            ),
            accumulated_reasoning,
        )

    if isinstance(event, ReasoningStreamEvent):
        # GPT-5 reasoning token
        new_accumulated = accumulated_reasoning + event.reasoning
        if event.is_complete:
            return (
                StreamEvent(
                    type=StreamEventType.REASONING_COMPLETED,
                    reasoning=event.reasoning,
                    agent_id=event.agent_id,
                ),
                new_accumulated,
            )
        return (
            StreamEvent(
                type=StreamEventType.REASONING_DELTA,
                reasoning=event.reasoning,
                agent_id=event.agent_id,
            ),
            new_accumulated,
        )

    if isinstance(event, MagenticAgentMessageEvent):
        # Agent streaming content
        text = ""
        if hasattr(event, "message") and event.message:
            text = getattr(event.message, "text", "") or ""

        if not text:
            return None, accumulated_reasoning

        # Check for metadata to determine event kind
        kind = None
        if hasattr(event, "stage"):
            kind = getattr(event, "stage", None)

        return (
            StreamEvent(
                type=StreamEventType.RESPONSE_DELTA,
                delta=text,
                agent_id=event.agent_id,
                kind=kind,
            ),
            accumulated_reasoning,
        )

    if isinstance(event, ExecutorCompletedEvent):
        # Phase completion events with typed messages
        data = getattr(event, "data", None)
        if data is None:
            return None, accumulated_reasoning

        # Map different phase message types to thoughts
        if isinstance(data, AnalysisMessage):
            return (
                StreamEvent(
                    type=StreamEventType.ORCHESTRATOR_THOUGHT,
                    message=f"Analysis complete: {data.complexity} complexity",
                    kind="analysis",
                    data={
                        "complexity": data.complexity,
                        "capabilities": list(data.capabilities) if data.capabilities else [],
                        "steps": list(data.steps) if data.steps else [],
                    },
                ),
                accumulated_reasoning,
            )

        if isinstance(data, RoutingMessage):
            agents = list(data.decision.assigned_to) if data.decision.assigned_to else []
            return (
                StreamEvent(
                    type=StreamEventType.ORCHESTRATOR_THOUGHT,
                    message=f"Routing decision: {data.decision.mode.value} mode with {agents}",
                    kind="routing",
                    data={
                        "mode": data.decision.mode.value,
                        "assigned_to": agents,
                        "subtasks": list(data.decision.subtasks) if data.decision.subtasks else [],
                    },
                ),
                accumulated_reasoning,
            )

        if isinstance(data, QualityMessage):
            return (
                StreamEvent(
                    type=StreamEventType.ORCHESTRATOR_THOUGHT,
                    message=f"Quality assessment: score {data.score:.1f}/10",
                    kind="quality",
                    data={
                        "score": data.score,
                        "missing": list(data.missing) if data.missing else [],
                        "improvements": list(data.improvements) if data.improvements else [],
                    },
                ),
                accumulated_reasoning,
            )

        if isinstance(data, ProgressMessage):
            return (
                StreamEvent(
                    type=StreamEventType.ORCHESTRATOR_MESSAGE,
                    message=f"Progress: {data.action}",
                    kind="progress",
                    data={"action": data.action, "feedback": data.feedback},
                ),
                accumulated_reasoning,
            )

        # Generic phase completion
        return (
            StreamEvent(
                type=StreamEventType.ORCHESTRATOR_MESSAGE,
                message="Phase completed",
                data={"phase_data": str(data)[:200]},
            ),
            accumulated_reasoning,
        )

    if isinstance(event, WorkflowOutputEvent):
        # Final output event
        result_text = ""
        if hasattr(event, "data"):
            data = event.data
            if isinstance(data, list) and data:
                # List of ChatMessage
                last_msg = data[-1]
                result_text = getattr(last_msg, "text", str(last_msg))
            elif hasattr(data, "result"):
                result_text = str(data.result)
            else:
                result_text = str(data)

        return (
            StreamEvent(
                type=StreamEventType.RESPONSE_COMPLETED,
                message=result_text,
            ),
            accumulated_reasoning,
        )

    # Unknown event type - skip
    logger.debug("Unknown event type", event_type=type(event).__name__)
    return None, accumulated_reasoning


async def _event_generator(
    workflow: Any,
    session: WorkflowSession,
    session_manager: Any,
    log_reasoning: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """Generate SSE events from workflow execution.

    Args:
        workflow: The SupervisorWorkflow instance.
        session: The workflow session metadata.
        session_manager: The session manager for status updates.
        log_reasoning: Whether to accumulate reasoning for logging.

    Yields:
        SSE-compatible dictionaries with event data.
    """
    accumulated_reasoning = ""
    has_error = False
    error_message = ""

    try:
        # Update session to running
        session_manager.update_status(
            session.workflow_id,
            WorkflowStatus.RUNNING,
            started_at=datetime.now(),
        )

        logger.info(
            f"Starting workflow stream: workflow_id={session.workflow_id}, "
            f"task_preview={session.task[:50]}"
        )

        # Yield initial orchestrator message
        yield StreamEvent(
            type=StreamEventType.ORCHESTRATOR_MESSAGE,
            message="Starting workflow execution...",
        ).to_sse_dict()

        # Stream workflow events
        async for event in workflow.run_stream(session.task):
            stream_event, accumulated_reasoning = _map_workflow_event(event, accumulated_reasoning)
            if stream_event is not None:
                # Log event in real-time for console visibility
                _log_stream_event(stream_event, session.workflow_id)
                yield stream_event.to_sse_dict()

    except Exception as e:
        has_error = True
        error_message = str(e)
        logger.error(
            f"Workflow stream error: workflow_id={session.workflow_id}, error={error_message}",
            exc_info=True,
        )

        # Yield error event with partial reasoning flag if applicable
        error_event = StreamEvent(
            type=StreamEventType.ERROR,
            error=error_message,
            reasoning_partial=bool(accumulated_reasoning) if accumulated_reasoning else None,
        )
        yield error_event.to_sse_dict()

    finally:
        # Update session status
        final_status = WorkflowStatus.FAILED if has_error else WorkflowStatus.COMPLETED
        session_manager.update_status(
            session.workflow_id,
            final_status,
            completed_at=datetime.now(),
        )

        # Log reasoning if configured and accumulated
        if log_reasoning and accumulated_reasoning:
            logger.info(
                f"Workflow reasoning captured: workflow_id={session.workflow_id}, "
                f"reasoning_length={len(accumulated_reasoning)}"
            )

        # Yield done event
        yield StreamEvent(type=StreamEventType.DONE).to_sse_dict()

        logger.info(
            f"Workflow stream completed: workflow_id={session.workflow_id}, "
            f"status={final_status.value}, had_error={has_error}"
        )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/chat",
    summary="Stream chat response",
    description="""
    Execute a workflow task and stream the response via Server-Sent Events.

    The endpoint returns an SSE stream with the following event types:
    - `orchestrator.message`: Status updates from the orchestrator
    - `orchestrator.thought`: Reasoning/analysis events (routing, quality, etc.)
    - `response.delta`: Incremental response text from agents
    - `response.completed`: Final response content
    - `reasoning.delta`: GPT-5 model reasoning tokens (when available)
    - `reasoning.completed`: End of reasoning stream
    - `error`: Error information (includes `reasoning_partial` if interrupted)
    - `done`: Stream completion marker

    Each event is JSON-encoded with at minimum a `type` field and `timestamp`.
    """,
    response_class=EventSourceResponse,
    responses={
        200: {
            "description": "SSE stream of workflow events",
            "content": {"text/event-stream": {}},
        },
        429: {
            "description": "Too many concurrent workflows",
            "content": {
                "application/json": {
                    "example": {"detail": "Maximum concurrent workflows (10) reached."}
                }
            },
        },
    },
)
async def chat_stream(
    request: ChatRequest,
    workflow: WorkflowDep,
    session_manager: SessionManagerDep,
) -> EventSourceResponse:
    """Stream chat responses via SSE.

    Args:
        request: The chat request with message and options.
        workflow: Injected SupervisorWorkflow instance.
        session_manager: Injected session manager.

    Returns:
        EventSourceResponse streaming workflow events.
    """
    msg_preview = request.message[:50] if len(request.message) > 50 else request.message
    sanitized_preview = msg_preview.replace('\r', '').replace('\n', '')
    logger.info(
        f"Chat stream request received: message_preview={sanitized_preview}, "
        f"stream={request.stream}, reasoning_effort={request.reasoning_effort}"
    )

    if not request.stream:
        # Non-streaming fallback - redirect to regular endpoint
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Non-streaming requests should use POST /api/v1/run instead.",
        )

    # Create session (will raise 429 if limit exceeded)
    session = session_manager.create_session(
        task=request.message,
        reasoning_effort=request.reasoning_effort,
    )

    # TODO: Apply reasoning_effort override to workflow if provided
    # This would require passing it through to the agent factory

    # Check if reasoning logging is enabled (from config)
    log_reasoning = False
    if hasattr(workflow, "config") and workflow.config:
        config = workflow.config
        if hasattr(config, "logging") and hasattr(config.logging, "log_reasoning"):
            log_reasoning = bool(config.logging.log_reasoning)

    async def generate():
        async for event_data in _event_generator(workflow, session, session_manager, log_reasoning):
            yield {"data": json.dumps(event_data)}

    return EventSourceResponse(generate())


@router.get(
    "/sessions",
    summary="List active workflow sessions",
    description="Returns a list of all workflow sessions (active and recent).",
)
async def list_sessions(
    session_manager: SessionManagerDep,
) -> list[WorkflowSession]:
    """List all workflow sessions.

    Args:
        session_manager: Injected session manager.

    Returns:
        List of workflow sessions.
    """
    return session_manager.list_sessions()


@router.get(
    "/sessions/{workflow_id}",
    summary="Get workflow session details",
    description="Returns details for a specific workflow session.",
)
async def get_session(
    workflow_id: str,
    session_manager: SessionManagerDep,
) -> WorkflowSession:
    """Get a specific workflow session.

    Args:
        workflow_id: The workflow ID.
        session_manager: Injected session manager.

    Returns:
        The workflow session.

    Raises:
        HTTPException: If session not found.
    """
    session = session_manager.get_session(workflow_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow session '{workflow_id}' not found.",
        )
    return session


@router.delete(
    "/sessions/{workflow_id}",
    summary="Cancel a workflow session",
    description="Cancels a running workflow session. Has no effect on completed sessions.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_session(
    workflow_id: str,
    session_manager: SessionManagerDep,
) -> None:
    """Cancel a running workflow session.

    Args:
        workflow_id: The workflow ID to cancel.
        session_manager: Injected session manager.

    Raises:
        HTTPException: If session not found.
    """
    session = session_manager.get_session(workflow_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow session '{workflow_id}' not found.",
        )

    # Only cancel if running
    if session.status in (WorkflowStatus.CREATED, WorkflowStatus.RUNNING):
        session_manager.update_status(
            workflow_id,
            WorkflowStatus.CANCELLED,
            completed_at=datetime.now(),
        )
        sanitized_workflow_id = workflow_id.replace('\n', '').replace('\r', '')
        logger.info(f"Cancelled workflow session: workflow_id={sanitized_workflow_id}")
