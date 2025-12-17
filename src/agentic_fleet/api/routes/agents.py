"""Agent routes.

Provides endpoints for listing and inspecting available agents.
Re-uses the agent listing from the main API router.
"""

import logging

from fastapi import APIRouter

from agentic_fleet.api.deps import WorkflowDep
from agentic_fleet.models import AgentInfo

logger = logging.getLogger(__name__)

router = APIRouter()


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
    agents: list[AgentInfo] = []

    source_agents = getattr(workflow, "agents", [])
    if not source_agents and hasattr(workflow, "context"):
        source_agents = getattr(workflow.context, "agents", [])

    iterator = source_agents.values() if isinstance(source_agents, dict) else source_agents

    for agent in iterator:
        agents.append(
            AgentInfo(
                name=getattr(agent, "name", "unknown"),
                description=getattr(agent, "description", getattr(agent, "instructions", "")),
                type="DSPyEnhancedAgent" if hasattr(agent, "enable_dspy") else "StandardAgent",
            )
        )
    return agents
