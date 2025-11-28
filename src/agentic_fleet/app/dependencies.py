"""FastAPI dependency injection and lifespan management.

This module provides dependency injection utilities and application
lifecycle management for the AgenticFleet API.
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status

from agentic_fleet.app.schemas import WorkflowSession, WorkflowStatus
from agentic_fleet.workflows.supervisor import SupervisorWorkflow, create_supervisor_workflow

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

MAX_CONCURRENT_WORKFLOWS = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "10"))


# =============================================================================
# Workflow Session Manager
# =============================================================================


class WorkflowSessionManager:
    """Manages active workflow sessions for streaming endpoints.

    Provides in-memory session storage with concurrent workflow limits.
    Thread-safe operations for session lifecycle management.
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_WORKFLOWS) -> None:
        """Initialize the session manager.

        Args:
            max_concurrent: Maximum number of concurrent active workflows.
        """
        self._sessions: dict[str, WorkflowSession] = {}
        self._max_concurrent = max_concurrent

    def create_session(
        self,
        task: str,
        reasoning_effort: str | None = None,
    ) -> WorkflowSession:
        """Create a new workflow session.

        Args:
            task: The task to execute.
            reasoning_effort: Optional reasoning effort override.

        Returns:
            The created WorkflowSession.

        Raises:
            HTTPException: If concurrent workflow limit is reached.
        """
        active_count = self.count_active()
        if active_count >= self._max_concurrent:
            logger.warning(
                f"Concurrent workflow limit reached: active={active_count}, max={self._max_concurrent}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Maximum concurrent workflows ({self._max_concurrent}) reached. Try again later.",
            )

        workflow_id = f"wf-{uuid4().hex[:12]}"
        session = WorkflowSession(
            workflow_id=workflow_id,
            task=task,
            status=WorkflowStatus.CREATED,
            created_at=datetime.now(),
            reasoning_effort=reasoning_effort,
        )
        self._sessions[workflow_id] = session

        task_preview = task[:50] if len(task) > 50 else task
        logger.info(
            f"Created workflow session: workflow_id={workflow_id}, task_preview={task_preview}"
        )
        return session

    def get_session(self, workflow_id: str) -> WorkflowSession | None:
        """Get a workflow session by ID.

        Args:
            workflow_id: The workflow ID.

        Returns:
            The session if found, None otherwise.
        """
        return self._sessions.get(workflow_id)

    def update_status(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Update a workflow session's status.

        Args:
            workflow_id: The workflow ID.
            status: New status to set.
            started_at: Optional started timestamp.
            completed_at: Optional completed timestamp.
        """
        session = self._sessions.get(workflow_id)
        if session:
            session.status = status
            if started_at:
                session.started_at = started_at
            if completed_at:
                session.completed_at = completed_at

            logger.debug(
                f"Updated workflow status: workflow_id={workflow_id}, status={status.value}"
            )

    def count_active(self) -> int:
        """Count currently active (running) workflows.

        Returns:
            Number of workflows in RUNNING status.
        """
        return sum(
            1
            for s in self._sessions.values()
            if s.status in (WorkflowStatus.CREATED, WorkflowStatus.RUNNING)
        )

    def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Remove old completed/failed sessions.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup.

        Returns:
            Number of sessions cleaned up.
        """
        now = datetime.now()
        to_remove = []

        for wid, session in self._sessions.items():
            if session.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
                age = (now - session.created_at).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(wid)

        for wid in to_remove:
            del self._sessions[wid]

        if to_remove:
            logger.info(f"Cleaned up old sessions: count={len(to_remove)}")

        return len(to_remove)

    def list_sessions(self) -> list[WorkflowSession]:
        """List all sessions.

        Returns:
            List of all workflow sessions.
        """
        return list(self._sessions.values())


# Global session manager instance
_session_manager: WorkflowSessionManager | None = None


def get_session_manager() -> WorkflowSessionManager:
    """Get the global session manager instance.

    Returns:
        The WorkflowSessionManager singleton.
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = WorkflowSessionManager()
    return _session_manager


# =============================================================================
# Workflow Dependency
# =============================================================================


def _get_workflow(request: Request) -> SupervisorWorkflow:
    """Extract the workflow instance from application state.

    Args:
        request: The incoming HTTP request.

    Returns:
        The SupervisorWorkflow instance stored in app state.
    """
    return request.app.state.workflow


# Annotated dependency for cleaner injection in route handlers
WorkflowDep = Annotated[SupervisorWorkflow, Depends(_get_workflow)]
SessionManagerDep = Annotated[WorkflowSessionManager, Depends(get_session_manager)]


# Legacy alias for backward compatibility
get_workflow = _get_workflow


# =============================================================================
# Lifespan Management
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events.

    Creates and initializes the SupervisorWorkflow on startup,
    and handles cleanup on shutdown.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after startup initialization is complete.
    """
    logger.info("Starting AgenticFleet API...")
    workflow = await create_supervisor_workflow()
    app.state.workflow = workflow

    # Initialize session manager
    global _session_manager
    _session_manager = WorkflowSessionManager()

    logger.info(f"AgenticFleet API ready: max_concurrent_workflows={MAX_CONCURRENT_WORKFLOWS}")
    yield

    # Cleanup
    logger.info("Shutting down AgenticFleet API...")
    _session_manager = None
