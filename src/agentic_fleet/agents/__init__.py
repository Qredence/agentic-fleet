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
        validate_tool,
    )
    from .foundry import FoundryAgentAdapter, FoundryAgentConfig, FoundryHostedAgent

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
    if name in ("create_workflow_agents", "validate_tool", "get_default_agent_metadata"):
        from . import coordinator as _coordinator

        return getattr(_coordinator, name)
    if name in ("FoundryAgentAdapter", "FoundryAgentConfig", "FoundryHostedAgent"):
        from . import foundry as _foundry

        return getattr(_foundry, name)
    raise AttributeError(name)
