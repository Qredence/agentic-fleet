"""Handlers for chat message events (dict-based and object-based)."""

from __future__ import annotations

from typing import Any

from agentic_fleet.api.events.config.routing_config import classify_event
from agentic_fleet.models import StreamEvent
from agentic_fleet.models.base import StreamEventType
from agentic_fleet.utils.infra.logging import setup_logger

logger = setup_logger(__name__)


def handle_chat_message_with_contents(
    event: Any, accumulated_reasoning: str
) -> tuple[StreamEvent | None, str]:
    """Handle generic chat message events with role and contents."""
    try:
        # event.contents is likely a list of dicts with type/text
        text_parts = []
        for c in getattr(event, "contents", []):
            if isinstance(c, dict):
                text_parts.append(c.get("text", ""))
            elif hasattr(c, "text"):
                text_parts.append(getattr(c, "text", ""))
        text = "\n".join(t for t in text_parts if t)
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        logger.warning("Failed to extract text from chat message contents: %s", exc, exc_info=True)
        text = ""

    if text:
        author_name = getattr(event, "author_name", None) or getattr(event, "author", None)
        role = getattr(event, "role", None)
        role_value = role.value if role is not None and hasattr(role, "value") else role

        # Emit agent messages as agent-level stream events only
        event_type = StreamEventType.AGENT_MESSAGE
        category, ui_hint = classify_event(event_type)
        return (
            StreamEvent(
                type=event_type,
                message=text,
                agent_id=getattr(event, "agent_id", None),
                author=author_name,
                role=role_value,
                kind=None,
                category=category,
                ui_hint=ui_hint,
            ),
            accumulated_reasoning,
        )

    return None, accumulated_reasoning


def handle_chat_message_with_text(
    event: Any, accumulated_reasoning: str
) -> tuple[StreamEvent | None, str]:
    """Handle ChatMessage-like objects with .text and .role."""
    text = getattr(event, "text", "") or ""
    if text:
        role = getattr(event, "role", None)
        role_value = role.value if role is not None and hasattr(role, "value") else role
        author_name = getattr(event, "author_name", None) or getattr(event, "author", None)
        agent_id = getattr(event, "agent_id", None) or author_name

        # Emit agent messages as agent-level stream events only
        msg_type = StreamEventType.AGENT_MESSAGE
        msg_category, msg_ui_hint = classify_event(msg_type)
        return (
            StreamEvent(
                type=msg_type,
                message=text,
                agent_id=agent_id,
                author=author_name,
                role=role_value,
                kind=None,
                category=msg_category,
                ui_hint=msg_ui_hint,
            ),
            accumulated_reasoning,
        )

    return None, accumulated_reasoning


def handle_dict_chat_message(
    event_dict: dict[str, Any], accumulated_reasoning: str
) -> tuple[StreamEvent | None, str]:
    """Handle dict-based chat_message events."""
    if event_dict.get("type") != "chat_message":
        return None, accumulated_reasoning

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
        elif role is not None and hasattr(role, "value"):
            role_value = role.value

        # Determine event type
        event_type = StreamEventType.AGENT_MESSAGE
        if event_dict.get("event") == "agent.output":
            event_type = StreamEventType.AGENT_OUTPUT

        category, ui_hint = classify_event(event_type)
        return (
            StreamEvent(
                type=event_type,
                message=text,
                agent_id=event_dict.get("agent_id") or author_name,
                author=author_name,
                role=role_value,
                kind=None,
                category=category,
                ui_hint=ui_hint,
            ),
            accumulated_reasoning,
        )

    return None, accumulated_reasoning
