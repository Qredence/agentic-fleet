"""Agents package public API.

Exports AgentFactory for creating ChatAgent instances from YAML configuration,
and create_workflow_agents for creating default workflow agents.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .coordinator import (
        AgentFactory,
        create_workflow_agents,
        get_default_agent_metadata,
    )
    from .foundry import FoundryAgentAdapter, FoundryAgentConfig, FoundryHostedAgent
    from .helpers import validate_tool

__all__ = [
    "AgentFactory",
    "FoundryAgentAdapter",
    "FoundryAgentConfig",
    "FoundryHostedAgent",
    "get_default_agent_metadata",
    "validate_tool",
]


def __getattr__(name: str) -> Any:
    if name == "AgentFactory":
        from . import coordinator as _coordinator

        return getattr(_coordinator, name)
    if name in ("create_workflow_agents", "get_default_agent_metadata"):
        from . import coordinator as _coordinator

        return getattr(_coordinator, name)
    if name == "validate_tool":
        from . import helpers as _helpers

        return getattr(_helpers, name)
    if name in ("FoundryAgentAdapter", "FoundryAgentConfig", "FoundryHostedAgent"):
        from . import foundry as _foundry

        return getattr(_foundry, name)
    raise AttributeError(name)
