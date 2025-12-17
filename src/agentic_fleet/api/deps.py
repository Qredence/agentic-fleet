"""FastAPI dependency injection utilities (template-style).

This module centralizes `Depends()` helpers and typed dependency aliases, similar
to FastAPI's full-stack template `api/deps.py`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from agentic_fleet.core.settings import AppSettings, get_settings
from agentic_fleet.services.conversation import ConversationManager, WorkflowSessionManager
from agentic_fleet.workflows.supervisor import SupervisorWorkflow


def get_workflow(request: Request) -> SupervisorWorkflow:
    """Get the SupervisorWorkflow from app state."""
    workflow = getattr(request.app.state, "workflow", None)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow not initialized. Service unavailable.",
        )
    return workflow


_get_workflow = get_workflow


def get_app_settings(request: Request) -> AppSettings:
    """Get typed settings from app state (fallback to env)."""
    settings = getattr(request.app.state, "settings", None)
    return settings or get_settings()


def get_session_manager(request: Request) -> WorkflowSessionManager:
    """Get the workflow session manager from app state."""
    manager = getattr(request.app.state, "session_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session manager not initialized. Service unavailable.",
        )
    return manager


def get_conversation_manager(request: Request) -> ConversationManager:
    """Get the conversation manager from app state."""
    manager = getattr(request.app.state, "conversation_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation manager not initialized. Service unavailable.",
        )
    return manager


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
    "get_session_manager",
    "get_workflow",
]
