import time
import uuid

from fastapi import APIRouter, HTTPException

from agentic_fleet.api.dependencies import Logger
from agentic_fleet.api.exceptions import WorkflowExecutionError
from agentic_fleet.api.models import WorkflowRunRequest, WorkflowRunResponse
from agentic_fleet.workflows.config import WorkflowConfig
from agentic_fleet.workflows.supervisor import create_supervisor_workflow

router = APIRouter()


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(request: WorkflowRunRequest, logger: Logger):
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

        workflow_config = WorkflowConfig(**inputs.get("config", {}))
        workflow = await create_supervisor_workflow(config=workflow_config)

        result = await workflow.run(task)

        execution_time = time.time() - start_time
        logger.info(f"Workflow run {run_id} completed in {execution_time:.2f}s")

        return WorkflowRunResponse(
            run_id=run_id,
            status="completed",
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
