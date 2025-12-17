"""Agent services facade.

Re-exports agent definitions, factory, and prompts from the agents package.
This provides a single import point for agent-related functionality.

Usage:
    from agentic_fleet.services.agents import AgentFactory
    from agentic_fleet.services.agents import create_workflow_agents
    from agentic_fleet.services.agents import get_planner_instructions
"""

from __future__ import annotations

from agentic_fleet.agents.base import DSPyEnhancedAgent
from agentic_fleet.agents.coordinator import (
    AgentFactory,
    create_workflow_agents,
    get_default_agent_metadata,
    validate_tool,
)
from agentic_fleet.agents.foundry import FoundryAgentAdapter
from agentic_fleet.agents.prompts import (
    get_coder_instructions,
    get_copilot_researcher_instructions,
    get_executor_instructions,
    get_generator_instructions,
    get_planner_instructions,
    get_verifier_instructions,
)

__all__ = [
    "AgentFactory",
    "DSPyEnhancedAgent",
    "FoundryAgentAdapter",
    "create_workflow_agents",
    "get_coder_instructions",
    "get_copilot_researcher_instructions",
    "get_default_agent_metadata",
    "get_executor_instructions",
    "get_generator_instructions",
    "get_planner_instructions",
    "get_verifier_instructions",
    "validate_tool",
]
