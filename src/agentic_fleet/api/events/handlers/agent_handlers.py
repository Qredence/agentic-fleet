"""Handlers for agent-level events (messages, reasoning, requests)."""

from __future__ import annotations

from typing import Any

from agent_framework._workflows import RequestInfoEvent

from agentic_fleet.api.events.config.routing_config import classify_event
from agentic_fleet.models import StreamEvent
from agentic_fleet.models.base import StreamEventType
from agentic_fleet.workflows.models import (
    MagenticAgentMessageEvent,
    ReasoningStreamEvent,
)


def serialize_request_payload(request_obj: Any) -> Any:
    """Best-effort serialization of request payload."""
    if request_obj is None:
        return None

    if hasattr(request_obj, "model_dump"):
        try:
            return request_obj.model_dump()
        except Exception:
            pass
    elif hasattr(request_obj, "to_dict"):
        try:
            return request_obj.to_dict()
        except Exception:
            pass
    elif isinstance(request_obj, dict):
        return request_obj

    return {
        "type": type(request_obj).__name__,
        "repr": repr(request_obj),
    }


def get_request_message(request_type_name: str | None) -> str:
    """Get UI message based on request type."""
    lowered = (request_type_name or "").lower()
    if "approval" in lowered:
        return "Tool approval required"
    elif "user" in lowered and "input" in lowered:
        return "User input required"
    elif "intervention" in lowered or "plan" in lowered:
        return "Human intervention required"
    return "Action required"


def handle_request_info(
    event: RequestInfoEvent, accumulated_reasoning: str
) -> tuple[StreamEvent, str]:
    """Handle agent-framework workflow request events (HITL)."""
    data = getattr(event, "data", None)
    request_id = None
    request_obj = None

    if data is not None:
        request_id = getattr(data, "request_id", None)
        request_obj = getattr(data, "request", None)
        if request_id is None and isinstance(data, dict):
            request_id = data.get("request_id")
            request_obj = data.get("request")

    if request_id is None:
        # Best-effort extraction for older shapes
        request_id = getattr(event, "request_id", None)

    request_type_name = type(request_obj).__name__ if request_obj is not None else None
    if request_type_name is None and data is not None:
        request_type_name = type(data).__name__

    # Best-effort serialization of the payload for the frontend
    payload = serialize_request_payload(request_obj)

    # Pick a UI message based on the request kind
    msg = get_request_message(request_type_name)

    event_type = StreamEventType.ORCHESTRATOR_MESSAGE
    kind = "request"
    category, ui_hint = classify_event(event_type, kind)
    return (
        StreamEvent(
            type=event_type,
            message=msg,
            agent_id="orchestrator",
            kind=kind,
            data={
                "request_id": request_id,
                "request_type": request_type_name,
                "request": payload,
            },
            category=category,
            ui_hint=ui_hint,
        ),
        accumulated_reasoning,
    )


def handle_reasoning_stream(
    event: ReasoningStreamEvent, accumulated_reasoning: str
) -> tuple[StreamEvent, str]:
    """Handle GPT-5 reasoning tokens."""
    new_accumulated = accumulated_reasoning + event.reasoning

    if event.is_complete:
        event_type = StreamEventType.REASONING_COMPLETED
        category, ui_hint = classify_event(event_type)
        return (
            StreamEvent(
                type=event_type,
                reasoning=event.reasoning,
                agent_id=event.agent_id,
                category=category,
                ui_hint=ui_hint,
            ),
            new_accumulated,
        )

    event_type = StreamEventType.REASONING_DELTA
    category, ui_hint = classify_event(event_type)
    return (
        StreamEvent(
            type=event_type,
            reasoning=event.reasoning,
            agent_id=event.agent_id,
            category=category,
            ui_hint=ui_hint,
        ),
        new_accumulated,
    )


def handle_agent_message(
    event: MagenticAgentMessageEvent, accumulated_reasoning: str
) -> tuple[StreamEvent | None, str]:
    """Handle agent-level message events."""
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
    event_name = None
    if hasattr(event, "event"):
        event_name = getattr(event, "event", None)
        if event_name == "agent.start":
            event_type = StreamEventType.AGENT_START
        elif event_name == "agent.output":
            event_type = StreamEventType.AGENT_OUTPUT
        elif event_name == "agent.complete" or event_name == "agent.completed":
            event_type = StreamEventType.AGENT_COMPLETE
        elif event_name == "handoff.created":
            # Handoff events should be surfaced as orchestrator thoughts
            event_type = StreamEventType.ORCHESTRATOR_THOUGHT
            kind = "handoff"  # Override kind for handoff events

    # Get author name - prefer message.author_name, fall back to agent_id
    author_name = None
    if hasattr(event, "message") and hasattr(event.message, "author_name"):
        author_name = getattr(event.message, "author_name", None)
    if not author_name:
        author_name = event.agent_id

    # Extract payload data for rich events (handoffs, tool calls, etc.)
    event_data = None
    if hasattr(event, "payload"):
        payload = getattr(event, "payload", None)
        if payload and isinstance(payload, dict):
            event_data = payload

    # Classify the event for UI routing
    category, ui_hint = classify_event(event_type, kind)

    return (
        StreamEvent(
            type=event_type,
            message=text,
            agent_id=event.agent_id,
            kind=kind,
            author=author_name,
            role="assistant",
            category=category,
            ui_hint=ui_hint,
            data=event_data,
        ),
        accumulated_reasoning,
    )
