"""Helpers for structured workflow streaming events."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from agent_framework import ChatMessage, MagenticAgentMessageEvent, Role

StreamPayload = Mapping[str, Any]


@dataclass(slots=True)
class StreamMetadata:
    """Metadata describing a streaming event."""

    stage: str
    event: str
    agent: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


def _attach_metadata(event: Any, metadata: StreamMetadata) -> Any:
    """Attach stage/event metadata to Magentic events (best-effort)."""

    event.stage = metadata.stage
    event.event = metadata.event
    event.payload = metadata.payload
    if metadata.agent and getattr(event, "agent_id", None) is None:
        event.agent_id = metadata.agent
    return event


def create_agent_event(
    *,
    stage: str,
    event: str,
    agent: str,
    text: str,
    payload: StreamPayload | None = None,
) -> MagenticAgentMessageEvent:
    """Build a structured MagenticAgentMessageEvent for agent activity."""

    message = ChatMessage(role=Role.ASSISTANT, text=text)
    metadata = StreamMetadata(stage=stage, event=event, agent=agent, payload=dict(payload or {}))
    return _attach_metadata(
        MagenticAgentMessageEvent(agent_id=agent or "unknown", message=message), metadata
    )


def create_system_event(
    *,
    stage: str,
    event: str,
    text: str,
    payload: StreamPayload | None = None,
    agent: str | None = None,
) -> MagenticAgentMessageEvent:
    """Build a structured event for non-agent/system updates."""

    message = ChatMessage(role=Role.ASSISTANT, text=text)
    metadata = StreamMetadata(stage=stage, event=event, agent=agent, payload=dict(payload or {}))
    return _attach_metadata(
        MagenticAgentMessageEvent(agent_id=agent or "system", message=message), metadata
    )
