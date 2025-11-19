"""Workflow routes for the Agentic Fleet API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agentic_fleet.api.models import WorkflowRequest, WorkflowResponse
from agentic_fleet.workflows.config import WorkflowConfig
from agentic_fleet.workflows.supervisor_workflow import create_supervisor_workflow

router = APIRouter()


@router.post("/run", response_model=WorkflowResponse)
async def run_workflow(request: WorkflowRequest) -> WorkflowResponse:
    """Execute a workflow synchronously (blocking until completion)."""

    try:
        # Initialize configuration
        config = WorkflowConfig(**(request.config or {}))

        # Create workflow
        workflow = await create_supervisor_workflow(config=config)

        # Run workflow
        result = await workflow.run(request.task)

        # Extract response data
        # Note: The result dict structure depends on the workflow implementation
        # We assume it matches the structure returned by SupervisorWorkflow.run()

        quality_data = result.get("quality", {})
        if hasattr(quality_data, "score"):  # Handle object vs dict
            score = quality_data.score
        else:
            score = float(quality_data.get("score", 0.0))

        return WorkflowResponse(
            result=str(result.get("result", "")),
            quality_score=score,
            execution_summary=result.get("execution_summary", {}),
            metadata=result.get("metadata", {}),
        )

    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
