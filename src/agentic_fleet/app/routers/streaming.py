"""Streaming chat endpoint using Server-Sent Events (SSE).

This module provides the streaming chat endpoint that converts
workflow events to SSE format for real-time frontend updates.
"""

from __future__ import annotations

import json
import re  # For robust input sanitization
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

from agentic_fleet.app.dependencies import ConversationManagerDep, SessionManagerDep, WorkflowDep
from agentic_fleet.app.schemas import (
    ChatRequest,
    MessageRole,
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
    event: WorkflowEvent | dict[str, Any],
    accumulated_reasoning: str,
) -> tuple[StreamEvent | list[StreamEvent] | None, str]:
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
        # Agent-level message (could be streaming or final). Surface explicitly so the frontend
        # can render per-agent thoughts/output instead of concatenated deltas.
        text = ""
        if hasattr(event, "message") and event.message:
            text = getattr(event.message, "text", "") or ""

        if not text:
            return None, accumulated_reasoning

        # Check for metadata to determine event kind/stage
        kind = None
        if hasattr(event, "stage"):
            kind = getattr(event, "stage", None)

        # Map the internal event type to the StreamEventType
        event_type = StreamEventType.AGENT_MESSAGE
        if hasattr(event, "event"):
            event_name = getattr(event, "event", None)
            if event_name == "agent.start":
                event_type = StreamEventType.AGENT_START
            elif event_name == "agent.output":
                event_type = StreamEventType.AGENT_OUTPUT
            elif event_name == "agent.complete" or event_name == "agent.completed":
                event_type = StreamEventType.AGENT_COMPLETE

        # Get author name - prefer message.author_name, fall back to agent_id
        author_name = None
        if hasattr(event, "message") and hasattr(event.message, "author_name"):
            author_name = getattr(event.message, "author_name", None)
        if not author_name:
            author_name = event.agent_id

        return (
            StreamEvent(
                type=event_type,
                message=text,
                agent_id=event.agent_id,
                kind=kind,
                author=author_name,
                role="assistant",
            ),
            accumulated_reasoning,
        )

    # Generic chat message events (agent_framework chat_message objects)
    if hasattr(event, "role") and hasattr(event, "contents"):
        try:
            # event.contents is likely a list of dicts with type/text
            text_parts = []
            for c in getattr(event, "contents", []):
                if isinstance(c, dict):
                    text_parts.append(c.get("text", ""))
                elif hasattr(c, "text"):
                    text_parts.append(getattr(c, "text", ""))
            text = "\n".join(t for t in text_parts if t)
        except Exception:
            text = ""

        if text:
            author_name = getattr(event, "author_name", None) or getattr(event, "author", None)
            role = getattr(event, "role", None)
            return (
                StreamEvent(
                    type=StreamEventType.AGENT_MESSAGE,
                    message=text,
                    agent_id=getattr(event, "agent_id", None),
                    author=author_name,
                    role=role.value if hasattr(role, "value") else role,
                    kind=None,
                ),
                accumulated_reasoning,
            )

    # ChatMessage-like objects with .text and .role (agent_framework ChatMessage)
    if hasattr(event, "text") and hasattr(event, "role"):
        text = getattr(event, "text", "") or ""
        if text:
            role = getattr(event, "role", None)
            author_name = getattr(event, "author_name", None) or getattr(event, "author", None)
            agent_id = getattr(event, "agent_id", None) or author_name
            return (
                StreamEvent(
                    type=StreamEventType.AGENT_MESSAGE,
                    message=text,
                    agent_id=agent_id,
                    author=author_name,
                    role=role.value if hasattr(role, "value") else role,
                    kind=None,
                ),
                accumulated_reasoning,
            )

    # Dict-based chat_message events (not objects)
    if isinstance(event, dict):
        event_dict: dict[str, Any] = event  # type: ignore
        if event_dict.get("type") == "chat_message":
            contents = event_dict.get("contents", [])
            text_parts: list[str] = []
            for c in contents:
                if isinstance(c, dict):
                    text_parts.append(c.get("text", ""))
                elif isinstance(c, str):
                    text_parts.append(c)
            text = "\n".join(t for t in text_parts if t)
            if text:
                author_name = event_dict.get("author_name") or event_dict.get("author")
                role = event_dict.get("role")

                # Handle role extraction safely
                role_value = role
                if isinstance(role, dict):
                    role_value = role.get("value")
                elif hasattr(role, "value"):
                    role_value = role.value

                # Determine event type
                event_type = StreamEventType.AGENT_MESSAGE
                if event_dict.get("event") == "agent.output":
                    event_type = StreamEventType.AGENT_OUTPUT

                return (
                    StreamEvent(
                        type=event_type,
                        message=text,
                        agent_id=event_dict.get("agent_id") or author_name,
                        author=author_name,
                        role=role_value,
                        kind=None,
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

    # Generic objects with .message.text and .role (safety net)
    if hasattr(event, "message") and hasattr(event.message, "text"):
        text = getattr(event.message, "text", "") or ""
        if text:
            role = getattr(event, "role", None) or getattr(event.message, "role", None)
            author_name = getattr(event, "author_name", None) or getattr(
                event.message, "author_name", None
            )
            agent_id = getattr(event, "agent_id", None) or getattr(event.message, "author", None)
            return (
                StreamEvent(
                    type=StreamEventType.AGENT_MESSAGE,
                    message=text,
                    agent_id=agent_id,
                    author=author_name,
                    role=role.value if hasattr(role, "value") else role,
                    kind=None,
                ),
                accumulated_reasoning,
            )

    if isinstance(event, WorkflowOutputEvent):
        # Final output event
        result_text = ""
        data = getattr(event, "data", None)

        if data is not None:
            if isinstance(data, list) and data:
                # List of ChatMessage
                last_msg = data[-1]
                result_text = getattr(last_msg, "text", str(last_msg))
            elif hasattr(data, "result"):
                result_text = str(data.result)
            else:
                result_text = str(data)

        events: list[StreamEvent] = []

        if isinstance(data, list) and data:
            for msg in data:
                text = getattr(msg, "text", None) or ""
                role = getattr(msg, "role", None)
                author = getattr(msg, "author_name", None) or getattr(msg, "author", None)
                agent_id = getattr(msg, "author", None)
                if text:
                    events.append(
                        StreamEvent(
                            type=StreamEventType.AGENT_MESSAGE,
                            message=text,
                            agent_id=agent_id,
                            author=author,
                            role=role.value if hasattr(role, "value") else role,
                        )
                    )

        # Always push a final completion event
        events.append(
            StreamEvent(
                type=StreamEventType.RESPONSE_COMPLETED,
                message=result_text,
            )
        )

        return events, accumulated_reasoning

    # Unknown event type - skip
    logger.debug(f"Unknown event type: {type(event).__name__}")
    return None, accumulated_reasoning


async def _event_generator(
    workflow: Any,
    session: WorkflowSession,
    session_manager: Any,
    log_reasoning: bool = False,
    reasoning_effort: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Generate SSE events from workflow execution.

    Args:
        workflow: The SupervisorWorkflow instance.
        session: The workflow session metadata.
        session_manager: The session manager for status updates.
        log_reasoning: Whether to accumulate reasoning for logging.
        reasoning_effort: Optional reasoning effort override for GPT-5 models.

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

        # Stream workflow events with optional reasoning effort override
        async for event in workflow.run_stream(session.task, reasoning_effort=reasoning_effort):
            stream_event, accumulated_reasoning = _map_workflow_event(event, accumulated_reasoning)
            if stream_event is not None:
                events_to_emit = stream_event if isinstance(stream_event, list) else [stream_event]
                for se in events_to_emit:
                    _log_stream_event(se, session.workflow_id)
                    yield se.to_sse_dict()

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
    conversation_manager: ConversationManagerDep,
) -> EventSourceResponse:
    """Stream chat responses via SSE.

    Args:
        request: The chat request with message and options.
        workflow: Injected SupervisorWorkflow instance.
        session_manager: Injected session manager.
        conversation_manager: Injected conversation manager.

    Returns:
        EventSourceResponse streaming workflow events.
    """
    msg_preview = request.message[:50] if len(request.message) > 50 else request.message
    # Remove all control chars (including \r, \n, tabs, Unicode separators) from user message before logging
    sanitized_preview = re.sub(r"[\x00-\x1F\x7F\u2028\u2029]", "", msg_preview)
    logger.info(
        f"Chat stream request received: message_preview={sanitized_preview}, "
        f"stream={request.stream}, reasoning_effort={request.reasoning_effort}, "
        f"conversation_id={request.conversation_id}"
    )

    if not request.stream:
        # Non-streaming fallback - redirect to regular endpoint
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Non-streaming requests should use POST /api/v1/run instead.",
        )

    # Save user message if conversation_id is provided
    if request.conversation_id:
        conversation_manager.add_message(
            request.conversation_id,
            MessageRole.USER,
            request.message,
            author="User",
        )

    # Create session (will raise 429 if limit exceeded)
    session = session_manager.create_session(
        task=request.message,
        reasoning_effort=request.reasoning_effort,
    )

    # Check if reasoning logging is enabled (from config)
    log_reasoning = False
    if hasattr(workflow, "config") and workflow.config:
        config = workflow.config
        if hasattr(config, "logging") and hasattr(config.logging, "log_reasoning"):
            log_reasoning = bool(config.logging.log_reasoning)

    async def generate():
        full_response = ""
        last_author: str | None = None
        last_agent_id: str | None = None

        async for event_data in _event_generator(
            workflow, session, session_manager, log_reasoning, request.reasoning_effort
        ):
            event_type = event_data.get("type")

            # Track author/agent metadata for final conversation save
            author = event_data.get("author") or event_data.get("agent_id")
            if author:
                last_author = event_data.get("author") or last_author or author
                last_agent_id = event_data.get("agent_id") or last_agent_id

            # Capture response content for history from various event types
            if event_type == StreamEventType.RESPONSE_DELTA.value:
                full_response += event_data.get("delta", "")
            elif event_type == StreamEventType.RESPONSE_COMPLETED.value:
                # Final response - use this as the definitive content
                completed_msg = event_data.get("message", "")
                if completed_msg:
                    full_response = completed_msg
                last_author = event_data.get("author") or last_author
            elif event_type in (
                StreamEventType.AGENT_OUTPUT.value,
                StreamEventType.AGENT_MESSAGE.value,
            ):
                # Capture agent output/message as response content
                agent_msg = event_data.get("message", "")
                if agent_msg:
                    full_response = agent_msg

            yield {"data": json.dumps(event_data)}

        # Save assistant message on completion if conversation_id provided
        if request.conversation_id and full_response:
            conversation_manager.add_message(
                request.conversation_id,
                MessageRole.ASSISTANT,
                full_response,
                author=last_author,
                agent_id=last_agent_id,
            )

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
        sanitized_workflow_id = workflow_id.replace("\n", "").replace("\r", "")
        logger.info(f"Cancelled workflow session: workflow_id={sanitized_workflow_id}")
