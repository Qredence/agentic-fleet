"""Workflow execution routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from agentic_fleet.api.deps import WorkflowDep
from agentic_fleet.models import RunRequest, RunResponse

# Langfuse integration for FastAPI route tracing
try:
    from langfuse.decorators import observe as langfuse_observe  # type: ignore[import-untyped]

    def observe(func=None, **kwargs):  # type: ignore
        """Langfuse observe decorator wrapper."""
        if func is None:
            # Called with @observe() - return a decorator
            return lambda f: langfuse_observe(f, **kwargs)
        # Called with @observe - apply directly
        return langfuse_observe(func, **kwargs)
except ImportError:

    def observe(func=None, **_kwargs):  # type: ignore
        """No-op decorator when Langfuse is not available."""
        if func is None:
            # Called with @observe() - return identity
            return lambda f: f
        # Called with @observe - return function as-is
        return func


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/types")
@observe()
async def list_workflow_types() -> list[str]:
    """List available workflow types supported by the system."""
    return ["SupervisorWorkflow"]


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
@observe
async def run_workflow(request: RunRequest, workflow: WorkflowDep) -> RunResponse:
    """Execute a workflow task."""
    try:
        result = await workflow.run(request.task)
        return RunResponse(
            result=str(result.get("result", "")),
            status=str(result.get("status", "completed")),
            execution_id=str(result.get("workflowId", result.get("execution_id", "unknown"))),
            metadata=result.get("metadata", {}) or {},
        )
    except Exception as exc:
        task_preview = request.task[:100].replace("\r", "").replace("\n", "")
        logger.exception("Workflow execution failed for task: %s", task_preview)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {exc}",
        ) from exc
