"""Helpers for structured workflow streaming events."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import WorkflowEvent

StreamPayload = Mapping[str, Any]


class MagenticAgentMessageEvent(WorkflowEvent):
    """Event wrapper for agent messages.

    Inherits from WorkflowEvent to ensure events added via ctx.add_event()
    are properly surfaced through the workflow's run_stream() output.
    """

    def __init__(
        self,
        agent_id: str,
        message: ChatMessage,
        stage: str | None = None,
        event: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the agent message event.

        Args:
            agent_id: The ID of the agent that produced this message.
            message: The ChatMessage content.
            stage: The workflow stage (e.g., 'execution').
            event: The event type (e.g., 'agent.start', 'agent.output').
            payload: Additional event metadata.
        """
        # Initialize parent with data for serialization
        super().__init__(data={"agent_id": agent_id})
        self.agent_id = agent_id
        self.message = message
        self.stage = stage
        self.event = event
        self.payload = payload or {}

    def __repr__(self) -> str:
        """Return a string representation of the event."""
        return (
            f"MagenticAgentMessageEvent(agent_id={self.agent_id!r}, "
            f"event={self.event!r}, stage={self.stage!r})"
        )


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
