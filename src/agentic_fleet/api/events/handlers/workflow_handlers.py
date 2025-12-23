"""Handlers for workflow-level events (started, status, output)."""

from __future__ import annotations

from typing import Any

from agent_framework._workflows import (
    WorkflowOutputEvent,
    WorkflowStartedEvent,
    WorkflowStatusEvent,
)

from agentic_fleet.api.events.config.routing_config import classify_event
from agentic_fleet.models import StreamEvent
from agentic_fleet.models.base import StreamEventType

# Valid workflow state names for WorkflowStatusEvent processing
VALID_WORKFLOW_STATES = {"FAILED", "IN_PROGRESS", "IDLE", "COMPLETED", "CANCELLED"}


def handle_workflow_started(
    _event: WorkflowStartedEvent,
    accumulated_reasoning: str,
) -> tuple[None, str]:
    """Skip generic WorkflowStartedEvent - covered by IN_PROGRESS status event."""
    return None, accumulated_reasoning


def handle_workflow_status(
    event: WorkflowStatusEvent, accumulated_reasoning: str
) -> tuple[StreamEvent | None, str]:
    """Handle WorkflowStatusEvent - convert FAILED to error, IN_PROGRESS to progress."""
    from agentic_fleet.utils.infra.logging import setup_logger

    logger = setup_logger(__name__)

    state = event.state
    data = event.data or {}
    message = data.get("message", "")
    workflow_id = data.get("workflow_id", "")

    # Convert state to a valid state name (enum or string), else skip with warning
    if hasattr(state, "name"):
        state_name = state.name
    elif isinstance(state, str):
        state_name = state.upper()
    else:
        logger.warning(
            f"Unrecognized workflow state type: {type(state)} ({state!r}) in WorkflowStatusEvent; skipping event."
        )
        return None, accumulated_reasoning

    if state_name not in VALID_WORKFLOW_STATES:
        logger.warning(
            f"Unrecognized workflow state value: {state_name!r} in WorkflowStatusEvent; skipping event."
        )
        return None, accumulated_reasoning

    if state_name == "FAILED":
        # Convert FAILED status to error event
        event_type = StreamEventType.ERROR
        category, ui_hint = classify_event(event_type)
        return (
            StreamEvent(
                type=event_type,
                error=message or "Workflow failed",
                data={"workflow_id": workflow_id, **data},
                category=category,
                ui_hint=ui_hint,
            ),
            accumulated_reasoning,
        )
    elif state_name == "IN_PROGRESS":
        # Convert IN_PROGRESS to orchestrator message with progress kind
        event_type = StreamEventType.ORCHESTRATOR_MESSAGE
        kind = "progress"
        category, ui_hint = classify_event(event_type, kind)
        return (
            StreamEvent(
                type=event_type,
                message=message or "Workflow started",
                kind=kind,
                data={"workflow_id": workflow_id, **data},
                category=category,
                ui_hint=ui_hint,
            ),
            accumulated_reasoning,
        )

    # Skip IDLE and other states
    return None, accumulated_reasoning


def handle_workflow_output(
    event: WorkflowOutputEvent, accumulated_reasoning: str
) -> tuple[list[StreamEvent], str]:
    """Handle final output event."""
    result_text = ""
    data = getattr(event, "data", None)

    # AgentRunResponse compatibility (framework 1.0+): unwrap messages and structured output
    structured_output = None
    messages: list[Any] = []

    if data is not None:
        if hasattr(data, "messages"):
            messages = list(getattr(data, "messages", []) or [])
            structured_output = getattr(data, "structured_output", None) or getattr(
                data, "additional_properties", {}
            ).get("structured_output")
        elif isinstance(data, list):
            messages = data

        if messages:
            last_msg = messages[-1]
            result_text = getattr(last_msg, "text", str(last_msg)) or str(last_msg)
        elif not isinstance(data, list) and hasattr(data, "result"):
            result_text = str(getattr(data, "result", ""))
        else:
            result_text = str(data)

    events: list[StreamEvent] = []

    if messages:
        for msg in messages:
            text = getattr(msg, "text", None) or getattr(msg, "content", "") or ""
            role = getattr(msg, "role", None)
            author = getattr(msg, "author_name", None) or getattr(msg, "author", None)
            agent_id = getattr(msg, "author", None)
            if text:
                msg_event_type = StreamEventType.AGENT_MESSAGE
                msg_category, msg_ui_hint = classify_event(msg_event_type)
                events.append(
                    StreamEvent(
                        type=msg_event_type,
                        message=text,
                        agent_id=agent_id,
                        author=author,
                        role=role.value if role is not None and hasattr(role, "value") else role,
                        category=msg_category,
                        ui_hint=msg_ui_hint,
                    )
                )

    # Always push a final completion event
    final_event_type = StreamEventType.RESPONSE_COMPLETED
    final_category, final_ui_hint = classify_event(final_event_type)
    events.append(
        StreamEvent(
            type=final_event_type,
            message=result_text,
            data={"structured_output": structured_output} if structured_output else None,
            category=final_category,
            ui_hint=final_ui_hint,
        )
    )

    return events, accumulated_reasoning
