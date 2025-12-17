"""Workflow session routes.

Provides endpoints to list, inspect, and cancel workflow sessions used by
streaming endpoints.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from agentic_fleet.api.deps import SessionManagerDep
from agentic_fleet.models import WorkflowSession, WorkflowStatus
from agentic_fleet.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.get(
    "/sessions",
    summary="List active workflow sessions",
    description="Returns a list of all workflow sessions (active and recent).",
)
async def list_sessions(session_manager: SessionManagerDep) -> list[WorkflowSession]:
    """List all workflow sessions (active and recent)."""
    return await session_manager.list_sessions()


@router.get(
    "/sessions/{workflow_id}",
    summary="Get workflow session details",
    description="Returns details for a specific workflow session.",
)
async def get_session(workflow_id: str, session_manager: SessionManagerDep) -> WorkflowSession:
    """Get details for a workflow session."""
    session = await session_manager.get_session(workflow_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow session '{workflow_id}' not found.",
        )
    return session


@router.delete(
    "/sessions/{workflow_id}",
    summary="Cancel a workflow session",
    description="Cancels a running workflow session. Has no effect on completed sessions.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_session(workflow_id: str, session_manager: SessionManagerDep) -> None:
    """Cancel a running workflow session."""
    session = await session_manager.get_session(workflow_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow session '{workflow_id}' not found.",
        )

    if session.status in (WorkflowStatus.CREATED, WorkflowStatus.RUNNING):
        await session_manager.update_status(
            workflow_id,
            WorkflowStatus.CANCELLED,
            completed_at=datetime.now(),
        )
        sanitized_workflow_id = workflow_id.replace("\n", "").replace("\r", "")
        logger.info("Cancelled workflow session: workflow_id=%s", sanitized_workflow_id)
