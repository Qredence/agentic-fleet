"""Execution history routes.

Provides endpoints for retrieving and managing workflow execution history.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, status

from agentic_fleet.api.deps import WorkflowDep
from agentic_fleet.core.storage import HistoryManager

router = APIRouter()


@router.get("/history", response_model=list[dict[str, Any]])
async def get_history(
    workflow: WorkflowDep,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum entries to return"),
    offset: int = Query(default=0, ge=0, description="Number of entries to skip"),
) -> list[dict[str, Any]]:
    """Retrieve recent workflow execution history (newest first)."""
    raw_history_manager = getattr(workflow, "history_manager", None)
    if raw_history_manager is None:
        return []

    history_manager = cast(HistoryManager, raw_history_manager)
    return history_manager.get_recent_executions(limit=limit, offset=offset)


@router.get("/history/{workflow_id}", response_model=dict[str, Any])
async def get_execution_details(
    workflow_id: str,
    workflow: WorkflowDep,
) -> dict[str, Any]:
    """Retrieve full details of a specific execution."""
    raw_history_manager = getattr(workflow, "history_manager", None)
    if raw_history_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History manager not available",
        )

    history_manager = cast(HistoryManager, raw_history_manager)
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
    raw_history_manager = getattr(workflow, "history_manager", None)
    if raw_history_manager is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History manager not available",
        )

    history_manager = cast(HistoryManager, raw_history_manager)
    deleted = history_manager.delete_execution(workflow_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {workflow_id} not found",
        )


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(workflow: WorkflowDep) -> None:
    """Clear all execution history."""
    raw_history_manager = getattr(workflow, "history_manager", None)
    if raw_history_manager is None:
        return

    history_manager = cast(HistoryManager, raw_history_manager)
    history_manager.clear_history()
