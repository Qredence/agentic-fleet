"""Event dispatch factory for mapping workflow events to stream events."""

from __future__ import annotations

from typing import Any

from agent_framework._workflows import (
    ExecutorCompletedEvent,
    RequestInfoEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
    WorkflowStatusEvent,
)

from agentic_fleet.api.events.handlers import EventHandler
from agentic_fleet.api.events.handlers.agent_handlers import (
    handle_agent_message,
    handle_reasoning_stream,
    handle_request_info,
)
from agentic_fleet.api.events.handlers.chat_handlers import (
    handle_chat_message_with_contents,
    handle_chat_message_with_text,
    handle_dict_chat_message,
)
from agentic_fleet.api.events.handlers.executor_handlers import (
    handle_executor_completed,
)
from agentic_fleet.api.events.handlers.workflow_handlers import (
    handle_workflow_output,
    handle_workflow_started,
    handle_workflow_status,
)
from agentic_fleet.models import StreamEvent
from agentic_fleet.utils.infra.logging import setup_logger
from agentic_fleet.workflows.models import (
    MagenticAgentMessageEvent,
    ReasoningStreamEvent,
)

logger = setup_logger(__name__)

# Dispatch table for O(1) event type lookup
_EVENT_HANDLERS: dict[type, EventHandler] = {
    WorkflowStartedEvent: handle_workflow_started,
    WorkflowStatusEvent: handle_workflow_status,
    RequestInfoEvent: handle_request_info,
    ReasoningStreamEvent: handle_reasoning_stream,
    MagenticAgentMessageEvent: handle_agent_message,
    ExecutorCompletedEvent: handle_executor_completed,
    WorkflowOutputEvent: handle_workflow_output,
}


def map_workflow_event(
    event: Any,
    accumulated_reasoning: str,
) -> tuple[StreamEvent | list[StreamEvent] | None, str]:
    """
    Convert an internal workflow event into one or more StreamEvent objects for SSE streaming.

    Uses a dispatch table for O(1) event type lookup instead of linear if/elif chain.
    This improves performance and maintainability by organizing event handling into focused
    handler functions that can be tested independently.

    Parameters:
        event: The workflow event to map. Supported inputs include framework event objects, dict-based events,
            and executor/message wrapper objects; the mapper performs safe extraction and duck-typing to
            recognize different event payloads.
        accumulated_reasoning: Running concatenation of reasoning text used to accumulate partial reasoning
            across ReasoningStreamEvent occurrences.

    Returns:
        A tuple where the first element is either a StreamEvent, a list of StreamEvent, or None if no event
        should be emitted, and the second element is the updated accumulated_reasoning string.
    """
    # O(1) dispatch table lookup for typed events
    event_type = type(event)
    handler = _EVENT_HANDLERS.get(event_type)

    if handler:
        return handler(event, accumulated_reasoning)

    # Fallback: check for duck-typed events (objects with role/contents or text/role)
    if hasattr(event, "role") and hasattr(event, "contents"):
        return handle_chat_message_with_contents(event, accumulated_reasoning)

    if hasattr(event, "text") and hasattr(event, "role"):
        return handle_chat_message_with_text(event, accumulated_reasoning)

    # Fallback: check for dict-based events
    if isinstance(event, dict):
        return handle_dict_chat_message(event, accumulated_reasoning)

    # Unknown event type - skip
    logger.debug(f"Unknown event type skipped: {type(event).__name__}")
    return None, accumulated_reasoning
