"""Manager classes for AgenticFleet API.

Provides ConversationManager and WorkflowSessionManager for managing
application state.
"""

import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status

from agentic_fleet.app.conversation_store import ConversationStore
from agentic_fleet.app.models import (
    Conversation,
    Message,
    MessageRole,
    WorkflowSession,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


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
        self._lock = asyncio.Lock()

    async def create_session(
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
        async with self._lock:
            active_count = self._count_active_locked()
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

    async def get_session(self, workflow_id: str) -> WorkflowSession | None:
        """Get a workflow session by ID.

        Args:
            workflow_id: The workflow ID.

        Returns:
            The session if found, None otherwise.
        """
        async with self._lock:
            return self._sessions.get(workflow_id)

    async def update_status(
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
        async with self._lock:
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

    async def count_active(self) -> int:
        """Count currently active (running) workflows.

        Returns:
            Number of workflows in RUNNING status.
        """
        async with self._lock:
            return self._count_active_locked()

    async def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Remove old completed/failed sessions.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup.

        Returns:
            Number of sessions cleaned up.
        """
        async with self._lock:
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

    async def list_sessions(self) -> list[WorkflowSession]:
        """List all sessions.

        Returns:
            List of all workflow sessions.
        """
        async with self._lock:
            return list(self._sessions.values())

    def _count_active_locked(self) -> int:
        return sum(
            1
            for s in self._sessions.values()
            if s.status in (WorkflowStatus.CREATED, WorkflowStatus.RUNNING)
        )
