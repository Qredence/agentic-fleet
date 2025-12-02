"""Workflow execution router.

Provides endpoints for running and managing workflow executions.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from agentic_fleet.app.dependencies import WorkflowDep
from agentic_fleet.app.schemas import RunRequest, RunResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
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
    """Execute a workflow task.

    Args:
        request: The workflow run request containing task details.
        workflow: The injected SupervisorWorkflow instance.

    Returns:
        RunResponse with execution results and metadata.

    Raises:
        HTTPException: If workflow execution fails.
    """
    try:
        result = await workflow.run(request.task)

        return RunResponse(
            result=str(result.get("result", "")),
            status=result.get("status", "completed"),
            execution_id=result.get("workflowId", result.get("execution_id", "unknown")),
            metadata=result.get("metadata", {}),
        )
    except Exception as e:
        logger.exception(
            "Workflow execution failed for task: %s",
            request.task[:100].replace("\r", "").replace("\n", ""),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {e}",
        ) from e
