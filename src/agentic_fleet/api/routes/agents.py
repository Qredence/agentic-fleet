"""Agent routes.

Provides endpoints for listing and inspecting available agents.
Re-uses the agent listing from the main API router.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from agentic_fleet.api.deps import WorkflowDep
from agentic_fleet.models import AgentInfo

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_agent_name(agent: Any) -> str:
    """Extract agent name from agent object."""
    return getattr(agent, "name", "unknown")


def _get_agent_description(agent: Any) -> str:
    """Extract agent description from agent object."""
    return getattr(agent, "description", None) or getattr(agent, "instructions", "")


def _get_agent_type(agent: Any) -> str:
    """Determine agent type based on capabilities."""
    return "DSPyEnhancedAgent" if hasattr(agent, "enable_dspy") else "StandardAgent"


@router.get(
    "/agents",
    response_model=list[AgentInfo],
    summary="List available agents",
    description="Returns a list of all agents available in the workflow.",
)
async def list_agents(workflow: WorkflowDep) -> list[AgentInfo]:
    """List all available agents in the workflow.

    Args:
        workflow: The injected SupervisorWorkflow instance.

    Returns:
        List of agent information objects.
    """
    source_agents = getattr(workflow, "agents", [])
    if not source_agents and hasattr(workflow, "context"):
        source_agents = getattr(workflow.context, "agents", [])

    iterator = source_agents.values() if isinstance(source_agents, dict) else source_agents

    return [
        AgentInfo(
            name=_get_agent_name(agent),
            description=_get_agent_description(agent),
            type=_get_agent_type(agent),
        )
        for agent in iterator
    ]
