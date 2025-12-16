"""Shared helpers for workflow execution strategies."""

from __future__ import annotations

from typing import Any

from agent_framework._agents import ChatAgent
from agent_framework._types import ChatMessage, Role

from ...utils.logger import setup_logger
from ..models import MagenticAgentMessageEvent

logger = setup_logger(__name__)


class ExecutionPhaseError(RuntimeError):
    """Raised when execution phase prerequisites are not satisfied."""


def _get_agent(agents: dict[str, ChatAgent], name: str) -> ChatAgent | None:
    """Get agent from map with case-insensitive lookup."""
    if name in agents:
        return agents[name]

    # Try case-insensitive match
    name_lower = name.lower()
    if name_lower in agents:
        return agents[name_lower]

    # Try stripping "Agent" suffix (e.g. "ResearcherAgent" -> "researcher")
    if name.endswith("Agent"):
        short_name = name[:-5].lower()
        if short_name in agents:
            return agents[short_name]

    # Try finding key that matches case-insensitive
    for key, agent in agents.items():
        if key.lower() == name_lower:
            return agent

    # Agent lookup failed - log available agents for debugging
    logger.warning("Agent lookup failed for '%s'. Available keys: %s", name, list(agents.keys()))
    return None


def _extract_tool_usage(response: Any) -> list[dict[str, Any]]:
    """Extract tool usage metadata from an agent response."""
    usage = []
    if hasattr(response, "messages"):
        for msg in response.messages:
            # Check for tool calls in the message (standard ChatMessage structure)
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    usage.append(
                        {
                            "tool": tool_call.get("name", "unknown"),
                            "arguments": tool_call.get("arguments", {}),
                            "timestamp": getattr(msg, "timestamp", None),
                        }
                    )
            # Check for tool usage in additional_properties (DSPy/custom agents)
            if hasattr(msg, "additional_properties"):
                props = msg.additional_properties
                if "tool_usage" in props:
                    usage.extend(props["tool_usage"])

    # Check top-level additional_properties if response itself has them
    if hasattr(response, "additional_properties"):
        props = response.additional_properties
        if props and "tool_usage" in props:
            usage.extend(props["tool_usage"])

    return usage


def create_agent_event(
    *,
    stage: str,
    event: str,
    agent: str,
    text: str,
    payload: dict[str, Any] | None = None,
) -> MagenticAgentMessageEvent:
    """Build a structured MagenticAgentMessageEvent for agent activity."""
    message = ChatMessage(role=Role.ASSISTANT, text=text)

    # Attach metadata to the event object dynamically
    evt = MagenticAgentMessageEvent(agent_id=agent, message=message)
    evt.stage = stage  # type: ignore[attr-defined]
    evt.event = event  # type: ignore[attr-defined]
    evt.payload = dict(payload or {})  # type: ignore[attr-defined]
    return evt


def create_system_event(
    *,
    stage: str,
    event: str,
    text: str,
    payload: dict[str, Any] | None = None,
    agent: str | None = None,
) -> MagenticAgentMessageEvent:
    """Build a structured event for non-agent/system updates."""
    message = ChatMessage(role=Role.ASSISTANT, text=text)

    evt = MagenticAgentMessageEvent(agent_id=agent or "System", message=message)
    evt.stage = stage  # type: ignore[attr-defined]
    evt.event = event  # type: ignore[attr-defined]
    evt.payload = dict(payload or {})  # type: ignore[attr-defined]
    return evt
