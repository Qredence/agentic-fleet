"""Conversation and session services.

This module contains the concrete implementations for:
- Conversation persistence (ConversationStore + ConversationManager)
- Streaming session tracking (WorkflowSessionManager)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status

from agentic_fleet.core.conversation_store import ConversationStore
from agentic_fleet.models import (
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
        """Create a new conversation."""
        conversation_id = str(uuid4())
        conversation = Conversation(id=conversation_id, title=title)
        saved = self._store.upsert(conversation)
        logger.info("Created conversation: %s", conversation_id)
        return saved

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        return self._store.get(str(conversation_id))

    def list_conversations(self) -> list[Conversation]:
        """List all conversations (updated_at desc)."""
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
        workflow_id: str | None = None,
        quality_score: float | None = None,
        quality_flag: str | None = None,
        quality_pending: bool = False,
        quality_details: dict[str, object] | None = None,
    ) -> Message | None:
        """Add a message to a conversation."""
        conversation = self._store.get(str(conversation_id))
        if not conversation:
            return None

        message = Message(
            role=role,
            content=content,
            author=author,
            agent_id=agent_id,
            workflow_id=workflow_id,
            quality_score=quality_score,
            quality_flag=quality_flag,
            quality_pending=quality_pending,
            quality_details=quality_details,
        )
        conversation.messages.append(message)
        conversation.updated_at = datetime.now()

        # Update title from first user message if still default
        if role == MessageRole.USER and conversation.title == "New Chat":
            new_title = content[:50].strip()
            if len(content) > 50:
                new_title += "..."
            conversation.title = new_title

        self._store.upsert(conversation)
        return message

    def update_message(
        self,
        conversation_id: str,
        message_id: str,
        *,
        quality_score: float | None = None,
        quality_flag: str | None = None,
        quality_pending: bool | None = None,
        quality_details: dict[str, object] | None = None,
    ) -> Message | None:
        """Update an existing message and persist the conversation."""
        conversation = self._store.get(str(conversation_id))
        if not conversation:
            return None

        updated: Message | None = None
        for idx, msg in enumerate(conversation.messages):
            if msg.id != message_id:
                continue

            patch: dict[str, object] = {}
            if quality_score is not None:
                patch["quality_score"] = float(quality_score)
            if quality_flag is not None:
                patch["quality_flag"] = str(quality_flag)
            if quality_pending is not None:
                patch["quality_pending"] = bool(quality_pending)
            if quality_details is not None:
                patch["quality_details"] = quality_details

            updated = msg.model_copy(update=patch)
            conversation.messages[idx] = updated
            conversation.updated_at = datetime.now()
            break

        if updated is None:
            return None

        self._store.upsert(conversation)
        return updated


class WorkflowSessionManager:
    """Manages active workflow sessions for streaming endpoints."""

    def __init__(self, max_concurrent: int = 10) -> None:
        self._sessions: dict[str, WorkflowSession] = {}
        self._max_concurrent = max_concurrent
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        task: str,
        reasoning_effort: str | None = None,
    ) -> WorkflowSession:
        """Create a new workflow session."""
        async with self._lock:
            active_count = self._count_active_locked()
            if active_count >= self._max_concurrent:
                logger.warning(
                    "Concurrent workflow limit reached: active=%s, max=%s",
                    active_count,
                    self._max_concurrent,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Maximum concurrent workflows "
                        f"({self._max_concurrent}) reached. Try again later."
                    ),
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
            "Created workflow session: workflow_id=%s, task_preview=%s",
            workflow_id,
            task_preview,
        )
        return session

    async def get_session(self, workflow_id: str) -> WorkflowSession | None:
        """Get a workflow session by ID."""
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
        """Update a workflow session's status."""
        async with self._lock:
            session = self._sessions.get(workflow_id)
            if session:
                session.status = status
                if started_at:
                    session.started_at = started_at
                if completed_at:
                    session.completed_at = completed_at

    async def count_active(self) -> int:
        """Count active workflows."""
        async with self._lock:
            return self._count_active_locked()

    async def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Remove old completed/failed sessions."""
        async with self._lock:
            now = datetime.now()
            to_remove: list[str] = []

            for workflow_id, session in self._sessions.items():
                if session.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
                    age = (now - session.created_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(workflow_id)

            for workflow_id in to_remove:
                del self._sessions[workflow_id]

        return len(to_remove)

    async def list_sessions(self) -> list[WorkflowSession]:
        """List all sessions."""
        async with self._lock:
            return list(self._sessions.values())

    def _count_active_locked(self) -> int:
        return sum(
            1
            for s in self._sessions.values()
            if s.status in (WorkflowStatus.CREATED, WorkflowStatus.RUNNING)
        )


__all__ = [
    "Conversation",
    "ConversationManager",
    "ConversationStore",
    "Message",
    "MessageRole",
    "WorkflowSession",
    "WorkflowSessionManager",
    "WorkflowStatus",
]
