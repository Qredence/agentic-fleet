"""Workflow API routes."""

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from agentic_fleet.api.dependencies import Logger, get_logger
from agentic_fleet.api.exceptions import WorkflowExecutionError
from agentic_fleet.api.models import WorkflowRunRequest, WorkflowRunResponse, WorkflowStatus
from agentic_fleet.workflows.config import WorkflowConfig
from agentic_fleet.workflows.supervisor import SupervisorWorkflow, create_supervisor_workflow

router = APIRouter()


async def get_workflow_factory(request: WorkflowRunRequest) -> SupervisorWorkflow:
    """Dependency to create a workflow instance."""
    inputs = request.inputs or {}
    workflow_config = WorkflowConfig(**inputs.get("config", {}))
    return await create_supervisor_workflow(config=workflow_config)


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(
    request: WorkflowRunRequest,
    logger: Annotated[Logger, Depends(get_logger)],
    workflow: Annotated[SupervisorWorkflow, Depends(get_workflow_factory)],
):
    """Run a workflow."""
    run_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        inputs = request.inputs or {}
        task = inputs.get("task") or request.workflow_id

        # Basic validation
        if not task or (len(task) < 5 and " " not in task):
            logger.warning(f"Invalid task provided: {task}")
            raise HTTPException(status_code=400, detail="Invalid task provided.")

        logger.info(f"Starting workflow run {run_id} for task: {task[:50]}...")

        result = await workflow.run(task)

        execution_time = time.time() - start_time
        logger.info(f"Workflow run {run_id} completed in {execution_time:.2f}s")

        return WorkflowRunResponse(
            run_id=run_id,
            status=WorkflowStatus.COMPLETED,
            output={
                "result": result.get("result"),
                "quality_score": result.get("quality", {}).get("score"),
                "execution_time": execution_time,
                "metadata": result.get("metadata", {}),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Workflow run {run_id} failed")
        raise WorkflowExecutionError(f"Workflow execution failed: {e!s}") from e
