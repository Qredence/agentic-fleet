"""FastAPI dependency injection utilities (template-style).

This module centralizes `Depends()` helpers and typed dependency aliases, similar
to FastAPI's full-stack template `api/deps.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, status

if TYPE_CHECKING:
    from fastapi import Request

from fastapi import Request

from agentic_fleet.services.conversation import ConversationManager, WorkflowSessionManager
from agentic_fleet.utils.cfg.settings import AppSettings, get_settings
from agentic_fleet.workflows.supervisor import SupervisorWorkflow


def _get_from_app_state[T](
    request: Request, attr_name: str, error_message: str, default: T | None = None
) -> T:
    """Get attribute from app state with error handling.

    Args:
        request: FastAPI request object
        attr_name: Name of the attribute in app.state
        error_message: Error message if attribute is missing
        default: Optional default value (if None, raises HTTPException)

    Returns:
        The attribute value

    Raises:
        HTTPException: If attribute is missing and no default provided
    """
    value = getattr(request.app.state, attr_name, default)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_message,
        )
    return value


def get_workflow(request: Request) -> SupervisorWorkflow:
    """Get the SupervisorWorkflow from app state."""
    return _get_from_app_state(
        request,
        "workflow",
        "Workflow not initialized. Service unavailable.",
    )


_get_workflow = get_workflow


def get_app_settings(request: Request) -> AppSettings:
    """Get typed settings from app state (fallback to env)."""
    settings = getattr(request.app.state, "settings", None)
    return settings or get_settings()


def get_session_manager(request: Request) -> WorkflowSessionManager:
    """Get the workflow session manager from app state."""
    return _get_from_app_state(
        request,
        "session_manager",
        "Session manager not initialized. Service unavailable.",
    )


def get_conversation_manager(request: Request) -> ConversationManager:
    """Get the conversation manager from app state."""
    return _get_from_app_state(
        request,
        "conversation_manager",
        "Conversation manager not initialized. Service unavailable.",
    )


async def get_or_create_workflow(request: Request) -> SupervisorWorkflow:
    """Get or create the supervisor workflow from app state.

    This helper centralizes workflow initialization logic used by streaming endpoints.
    Creates the workflow if it doesn't exist in app.state.supervisor_workflow.

    Args:
        request: FastAPI request object

    Returns:
        SupervisorWorkflow instance
    """
    workflow = getattr(request.app.state, "supervisor_workflow", None)
    if workflow is not None:
        return workflow

    # Lazy imports to avoid circular dependencies
    from agentic_fleet.utils.cfg import load_config
    from agentic_fleet.workflows.config import build_workflow_config_from_yaml
    from agentic_fleet.workflows.supervisor import create_supervisor_workflow

    yaml_config = getattr(request.app.state, "yaml_config", None)
    if yaml_config is None:
        yaml_config = load_config(validate=False)

    workflow_config = build_workflow_config_from_yaml(
        yaml_config,
        compile_dspy=False,
    )

    workflow = await create_supervisor_workflow(
        compile_dspy=False,
        config=workflow_config,
        dspy_routing_module=getattr(request.app.state, "dspy_routing_module", None),
        dspy_quality_module=getattr(request.app.state, "dspy_quality_module", None),
        dspy_tool_planning_module=getattr(request.app.state, "dspy_tool_planning_module", None),
    )
    request.app.state.supervisor_workflow = workflow
    return workflow


# Annotated dependency types for cleaner injection in route handlers
WorkflowDep = Annotated[SupervisorWorkflow, Depends(get_workflow)]
SessionManagerDep = Annotated[WorkflowSessionManager, Depends(get_session_manager)]
ConversationManagerDep = Annotated[ConversationManager, Depends(get_conversation_manager)]
SettingsDep = Annotated[AppSettings, Depends(get_app_settings)]

__all__ = [
    "ConversationManagerDep",
    "SessionManagerDep",
    "SettingsDep",
    "WorkflowDep",
    "_get_workflow",
    "get_app_settings",
    "get_conversation_manager",
    "get_or_create_workflow",
    "get_session_manager",
    "get_workflow",
]
