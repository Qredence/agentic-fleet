"""FastAPI dependency injection functions.

Provides dependency functions for use with FastAPI's Depends() pattern.
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from agentic_fleet.app.settings import AppSettings
from agentic_fleet.workflows.supervisor import SupervisorWorkflow

from .lifespan import get_conversation_manager, get_session_manager
from .managers import ConversationManager, WorkflowSessionManager

logger = logging.getLogger(__name__)


def _get_workflow(request: Request) -> SupervisorWorkflow:
    """Extract the workflow instance from application state.

    Args:
        request: The incoming HTTP request.

    Returns:
        The SupervisorWorkflow instance stored in app state.
    """
    workflow = getattr(request.app.state, "workflow", None)
    if workflow is None:
        logger.warning(
            "Workflow requested before initialization; returning 503 Service Unavailable"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow not initialized. Service unavailable.",
        )

    return workflow


def _get_settings(request: Request) -> AppSettings:
    """Extract settings from application state.

    Args:
        request: The incoming HTTP request.

    Returns:
        The AppSettings instance stored in app state.
    """
    return request.app.state.settings


# Annotated dependency types for cleaner injection in route handlers
WorkflowDep = Annotated[SupervisorWorkflow, Depends(_get_workflow)]
SessionManagerDep = Annotated[WorkflowSessionManager, Depends(get_session_manager)]
ConversationManagerDep = Annotated[ConversationManager, Depends(get_conversation_manager)]
SettingsDep = Annotated[AppSettings, Depends(_get_settings)]

# Legacy aliases for backward compatibility
get_workflow = _get_workflow
