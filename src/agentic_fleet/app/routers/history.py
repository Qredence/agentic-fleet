"""Execution history router.

Provides endpoints for retrieving workflow execution history.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from agentic_fleet.app.dependencies import WorkflowDep

router = APIRouter()


@router.get("/history", response_model=list[dict[str, Any]])
async def get_history(
    workflow: WorkflowDep,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum entries to return"),
    offset: int = Query(default=0, ge=0, description="Number of entries to skip"),
) -> list[dict[str, Any]]:
    """Retrieve recent workflow execution history.

    Returns the most recent executions, ordered by newest first.

    Args:
        workflow: The injected SupervisorWorkflow instance.
        limit: Maximum number of history entries to return (1-100).
        offset: Number of entries to skip.

    Returns:
        List of execution history records.
    """
    if not workflow.history_manager:
        return []

    if hasattr(workflow.history_manager, "get_recent_executions"):
        return workflow.history_manager.get_recent_executions(limit=limit, offset=offset)

    # Fallback for backward compatibility (returns chronological order)
    return workflow.history_manager.load_history(limit=limit)


@router.get("/history/{workflow_id}", response_model=dict[str, Any])
async def get_execution_details(
    workflow_id: str,
    workflow: WorkflowDep,
) -> dict[str, Any]:
    """Retrieve full details of a specific execution.

    Args:
        workflow_id: The ID of the workflow execution.
        workflow: The injected SupervisorWorkflow instance.

    Returns:
        The execution details.

    Raises:
        HTTPException: If the execution is not found.
    """
    if not workflow.history_manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History manager not available",
        )

    execution = workflow.history_manager.get_execution(workflow_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {workflow_id} not found",
        )

    return execution


@router.delete("/history/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(
    workflow_id: str,
    workflow: WorkflowDep,
) -> None:
    """Delete a specific execution record.

    Args:
        workflow_id: The ID of the workflow execution to delete.
        workflow: The injected SupervisorWorkflow instance.

    Raises:
        HTTPException: If the execution is not found or cannot be deleted.
    """
    if not workflow.history_manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History manager not available",
        )

    deleted = workflow.history_manager.delete_execution(workflow_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {workflow_id} not found",
        )


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    workflow: WorkflowDep,
) -> None:
    """Clear all execution history.

    Args:
        workflow: The injected SupervisorWorkflow instance.
    """
    if not workflow.history_manager:
        return

    workflow.history_manager.clear_history()
