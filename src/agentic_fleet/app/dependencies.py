"""FastAPI dependency injection and lifespan management.

This module provides dependency injection utilities and application
lifecycle management for the AgenticFleet API.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status

from agentic_fleet.app.conversation_store import ConversationStore
from agentic_fleet.app.schemas import (
    Conversation,
    Message,
    MessageRole,
    WorkflowSession,
    WorkflowStatus,
)
from agentic_fleet.app.settings import AppSettings, get_settings
from agentic_fleet.workflows.supervisor import SupervisorWorkflow, create_supervisor_workflow

logger = logging.getLogger(__name__)

# =============================================================================
# Conversation Manager
# =============================================================================


class ConversationManager:
    """Manages chat conversations backed by a JSON store."""

    def __init__(self, store: ConversationStore | None = None) -> None:
        self._store = store or ConversationStore()

    def create_conversation(self, title: str = "New Chat") -> Conversation:
        """Create a new conversation.

        Args:
            title: The title of the conversation.

        Returns:
            The created Conversation.
        """
        conversation_id = str(uuid4())

        conversation = Conversation(id=conversation_id, title=title)
        saved = self._store.upsert(conversation)
        logger.info(f"Created conversation: {conversation_id}")
        return saved

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation ID.

        Returns:
            The conversation if found, None otherwise.
        """
        return self._store.get(str(conversation_id))

    def list_conversations(self) -> list[Conversation]:
        """List all conversations.

        Returns:
            List of all conversations, sorted by update time desc.
        """
        conversations = self._store.list_conversations()
        return sorted(conversations, key=lambda c: c.updated_at, reverse=True)

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        *,
        author: str | None = None,
        agent_id: str | None = None,
    ) -> Message | None:
        """Add a message to a conversation.

        Args:
            conversation_id: The conversation ID.
            role: The sender role.
            content: The message content.
            author: Optional author/agent name.
            agent_id: Optional agent identifier.

        Returns:
            The added Message if conversation exists, None otherwise.
        """
        conversation = self._store.get(str(conversation_id))
        if not conversation:
            return None

        message = Message(role=role, content=content, author=author, agent_id=agent_id)
        conversation.messages.append(message)
        conversation.updated_at = datetime.now()

        # Update title from first user message if still default
        if role == MessageRole.USER and conversation.title == "New Chat":
            # Use first 50 chars of message as title
            new_title = content[:50].strip()
            if len(content) > 50:
                new_title += "..."
            conversation.title = new_title

        self._store.upsert(conversation)
        return message


# Global conversation manager instance
_conversation_manager: ConversationManager | None = None


def get_conversation_manager() -> ConversationManager:
    """Get the global conversation manager instance."""

    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


# =============================================================================
# Workflow Session Manager
# =============================================================================


class WorkflowSessionManager:
    """Manages active workflow sessions for streaming endpoints.

    Provides in-memory session storage with concurrent workflow limits.
    Thread-safe operations for session lifecycle management.
    """

    def __init__(self, max_concurrent: int = 10) -> None:
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
    """Get the global session manager instance."""

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
ConversationManagerDep = Annotated[ConversationManager, Depends(get_conversation_manager)]


# Legacy alias for backward compatibility
get_workflow = _get_workflow


def _get_settings(request: Request) -> AppSettings:
    return request.app.state.settings


SettingsDep = Annotated[AppSettings, Depends(_get_settings)]


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

    settings = get_settings()
    app.state.settings = settings

    workflow = await create_supervisor_workflow()
    app.state.workflow = workflow

    # Initialize managers with settings-aware configuration
    global _session_manager, _conversation_manager
    _session_manager = WorkflowSessionManager(max_concurrent=settings.max_concurrent_workflows)
    _conversation_manager = ConversationManager(ConversationStore(settings.conversations_path))

    logger.info(
        "AgenticFleet API ready: max_concurrent_workflows=%s, conversations_path=%s",
        settings.max_concurrent_workflows,
        settings.conversations_path,
    )
    yield

    # Cleanup
    logger.info("Shutting down AgenticFleet API...")
    _session_manager = None
    _conversation_manager = None
