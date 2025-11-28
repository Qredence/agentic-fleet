"""Agent management router.

Provides endpoints for listing and inspecting available agents.
"""

from fastapi import APIRouter

from agentic_fleet.app.dependencies import WorkflowDep
from agentic_fleet.app.schemas import AgentInfo

router = APIRouter()


@router.get(
    "/agents",
    response_model=list[AgentInfo],
    responses={200: {"description": "List of available agents"}},
)
async def get_agents(workflow: WorkflowDep) -> list[AgentInfo]:
    """List all available agents in the workflow.

    Args:
        workflow: The injected SupervisorWorkflow instance.

    Returns:
        List of AgentInfo objects describing available agents.
    """
    agents: list[AgentInfo] = []

    # Access agents from workflow.agents or workflow.context.agents
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
