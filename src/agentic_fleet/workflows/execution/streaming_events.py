"""Helpers for structured workflow streaming events."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import MagenticAgentMessageEvent

StreamPayload = Mapping[str, Any]


@dataclass(slots=True)
class StreamMetadata:
    """Metadata describing a streaming event."""

    stage: str
    event: str
    agent: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReasoningStreamEvent:
    """Event for streaming GPT-5 verbose reasoning tokens.

    This event type captures reasoning/chain-of-thought output from
    GPT-5 series models separately from the main response content.

    Attributes:
        reasoning: The reasoning text delta.
        agent_id: The agent that produced this reasoning (if applicable).
        is_complete: Whether this marks the end of reasoning output.
    """

    reasoning: str
    agent_id: str | None = None
    is_complete: bool = False


def _attach_metadata(
    event: MagenticAgentMessageEvent, metadata: StreamMetadata
) -> MagenticAgentMessageEvent:
    """Attach stage/event metadata to Magentic events (best-effort)."""

    event.stage = metadata.stage  # type: ignore[attr-defined]
    event.event = metadata.event  # type: ignore[attr-defined]
    event.payload = metadata.payload  # type: ignore[attr-defined]
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
