"""Execution history routes.

Provides endpoints for retrieving and managing workflow execution history.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, status

from agentic_fleet.api.deps import WorkflowDep
from agentic_fleet.utils.storage.history import HistoryManager

router = APIRouter()


def _get_history_manager(workflow: WorkflowDep, required: bool = True) -> HistoryManager | None:
    """Get history manager from workflow.

    Args:
        workflow: The workflow instance
        required: If True, raises HTTPException when not available

    Returns:
        HistoryManager instance or None if not required and not available

    Raises:
        HTTPException: If required and history manager is not available
    """
    raw_history_manager = getattr(workflow, "history_manager", None)
    if raw_history_manager is None:
        if required:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="History manager not available",
            )
        return None
    return cast(HistoryManager, raw_history_manager)


@router.get("/history", response_model=list[dict[str, Any]])
async def get_history(
    workflow: WorkflowDep,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum entries to return"),
    offset: int = Query(default=0, ge=0, description="Number of entries to skip"),
) -> list[dict[str, Any]]:
    """Retrieve recent workflow execution history (newest first)."""
    history_manager = _get_history_manager(workflow, required=False)
    if history_manager is None:
        return []
    return history_manager.get_recent_executions(limit=limit, offset=offset)


@router.get("/history/{workflow_id}", response_model=dict[str, Any])
async def get_execution_details(
    workflow_id: str,
    workflow: WorkflowDep,
) -> dict[str, Any]:
    """Retrieve full details of a specific execution."""
    history_manager = _get_history_manager(workflow)
    assert history_manager is not None  # Required=True ensures this
    execution = history_manager.get_execution(workflow_id)
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
    """Delete a specific execution record."""
    history_manager = _get_history_manager(workflow)
    assert history_manager is not None  # Required=True ensures this
    deleted = history_manager.delete_execution(workflow_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {workflow_id} not found",
        )


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(workflow: WorkflowDep) -> None:
    """Clear all execution history."""
    history_manager = _get_history_manager(workflow, required=False)
    if history_manager is not None:
        history_manager.clear_history()
