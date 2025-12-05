"""Unified API router for core endpoints.

Combines agent listing and workflow execution into a single module
to simplify router registration.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from agentic_fleet.app.dependencies import WorkflowDep
from agentic_fleet.app.schemas import AgentInfo, RunRequest, RunResponse

logger = logging.getLogger(__name__)

# Versioned API routes (/api/v1)
api_router = APIRouter()


@api_router.get(
    "/agents",
    response_model=list[AgentInfo],
    responses={200: {"description": "List of available agents"}},
)
async def get_agents(workflow: WorkflowDep) -> list[AgentInfo]:
    """List all available agents in the workflow."""
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


@api_router.post(
    "/run",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Workflow executed successfully"},
        422: {"description": "Validation error"},
        500: {"description": "Workflow execution failed"},
    },
)
async def run_workflow(request: RunRequest, workflow: WorkflowDep) -> RunResponse:
    """Execute a workflow task."""
    try:
        result = await workflow.run(request.task)

        return RunResponse(
            result=str(result.get("result", "")),
            status=result.get("status", "completed"),
            execution_id=result.get("workflowId", result.get("execution_id", "unknown")),
            metadata=result.get("metadata", {}),
        )
    except Exception as exc:
        task_preview = request.task[:100].replace("\r", "").replace("\n", "")
        logger.exception("Workflow execution failed for task: %s", task_preview)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {exc}",
        ) from exc
