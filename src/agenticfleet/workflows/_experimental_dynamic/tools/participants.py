"""Tool participant creation for the dynamic workflow."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from agent_framework import AgentProtocol

from agenticfleet.core.logging import get_logger

from .base_generator import create_base_generator_participant
from .google_search import create_google_search_participant
from .python_coder import create_python_coder_participant
from .wikipedia_search import create_wikipedia_search_participant

logger = get_logger(__name__)


def create_tool_factories() -> Mapping[str, Callable[[], AgentProtocol]]:
    """Return lazily evaluated factories for optional tool agents."""
    factories: dict[str, Callable[[], AgentProtocol]] = {
        "base_generator": lambda: create_base_generator_participant(),
    }

    factories["google_search"] = lambda: create_google_search_participant()
    factories["wikipedia_search"] = lambda: create_wikipedia_search_participant()
    factories["python_coder"] = lambda: create_python_coder_participant()

    return factories


def create_tool_participants(
    include_tool_agents: bool = True,
) -> Mapping[str, AgentProtocol]:
    """Instantiate the configured tool participants."""
    if not include_tool_agents:
        return {}

    participants: dict[str, AgentProtocol] = {}
    for name, factory in create_tool_factories().items():
        try:
            participants[name] = factory()
        except Exception as error:  # pragma: no cover - defensive guard
            logger.warning("Failed to create tool participant '%s': %s", name, error)
    return participants


__all__ = ["create_tool_factories", "create_tool_participants"]
