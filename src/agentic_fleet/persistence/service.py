"""Conversation persistence service integrating all repositories."""

from __future__ import annotations

import time
import uuid
from typing import Any

from openai import AsyncOpenAI

from .database import DatabaseManager
from .repositories import (
    ConversationRepository,
    EventRepository,
    LedgerRepository,
    MessageRepository,
    ReasoningRepository,
)
from .settings import PersistenceSettings
from .summarization import SummarizationPolicy, create_summary_message


class ConversationPersistenceService:
    """High-level service for conversation persistence operations."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        settings: PersistenceSettings | None = None,
        openai_client: AsyncOpenAI | None = None,
    ) -> None:
        """Initialize persistence service.

        Args:
            db_manager: Database manager
            settings: Persistence settings (uses defaults if not provided)
            openai_client: Optional OpenAI client for summarization
        """
        self.db_manager = db_manager
        self.settings = settings or PersistenceSettings()
        self._openai_client = openai_client

        # Initialize summarization policy
        self.summarization_policy = SummarizationPolicy(
            threshold=self.settings.summary_threshold,
            keep_recent=self.settings.summary_keep_recent,
            openai_client=openai_client,
        )

    async def create_conversation(
        self,
        workflow_id: str,
        conversation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new conversation.

        Args:
            workflow_id: Workflow ID
            conversation_id: Optional conversation ID (generated if not provided)
            metadata: Optional metadata

        Returns:
            Conversation ID
        """
        conversation_id = conversation_id or str(uuid.uuid4())

        async with self.db_manager.connection() as db:
            conv_repo = ConversationRepository(db)
            await conv_repo.create(conversation_id, workflow_id, metadata)

        return conversation_id

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        reasoning: str | None = None,
        agent_id: str | None = None,
        message_id: str | None = None,
        emit_event: bool = True,
    ) -> dict[str, Any]:
        """Add a message to conversation with optional auto-summarization.

        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant/system)
            content: Message content
            reasoning: Optional reasoning trace
            agent_id: Optional agent ID
            message_id: Optional message ID (generated if not provided)
            emit_event: Whether to emit event for this message

        Returns:
            Message dictionary with sequence
        """
        message_id = message_id or str(uuid.uuid4())

        async with self.db_manager.connection() as db:
            conv_repo = ConversationRepository(db)
            message_repo = MessageRepository(db)
            event_repo = EventRepository(db)
            reasoning_repo = ReasoningRepository(db)

            # Get next sequence
            sequence = await conv_repo.get_next_sequence(conversation_id)

            # Add message
            await message_repo.add(
                message_id=message_id,
                conversation_id=conversation_id,
                sequence=sequence,
                role=role,
                content=content,
                reasoning=reasoning,
                agent_id=agent_id,
            )

            # Store reasoning trace separately if enabled
            if reasoning and self.settings.enable_reasoning_traces:
                await reasoning_repo.add(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    reasoning_text=reasoning,
                    metadata={"role": role, "agent_id": agent_id},
                )

            # Emit message event if requested
            if emit_event and self.settings.enable_sequencing:
                await event_repo.add(
                    conversation_id=conversation_id,
                    sequence=sequence,
                    event_type="message.added",
                    event_data={
                        "message_id": message_id,
                        "role": role,
                        "has_reasoning": reasoning is not None,
                        "agent_id": agent_id,
                    },
                )

            # Check summarization threshold
            # Summarization is restricted to assistant messages to avoid interrupting user input flow and to ensure complete exchanges are summarized.
            if role == "assistant":  # Only check after assistant responses
                summary_meta = await self.summarization_policy.check_and_summarize(
                    conversation_id, message_repo, reasoning_repo
                )

                if summary_meta:
                    # Create summary message
                    summary_sequence = await conv_repo.get_next_sequence(conversation_id)
                    await create_summary_message(
                        message_repo,
                        conversation_id,
                        summary_sequence,
                        summary_meta,
                    )

            return {
                "id": message_id,
                "conversation_id": conversation_id,
                "sequence": sequence,
                "role": role,
                "content": content,
                "reasoning": reasoning,
                "agent_id": agent_id,
                "created_at": time.time(),
            }

    async def add_event(
        self,
        conversation_id: str,
        event_type: str,
        event_data: dict[str, Any],
    ) -> int:
        """Add an event with automatic sequencing.

        Args:
            conversation_id: Conversation ID
            event_type: Event type
            event_data: Event data

        Returns:
            Event sequence number
        """
        async with self.db_manager.connection() as db:
            conv_repo = ConversationRepository(db)
            event_repo = EventRepository(db)

            sequence = await conv_repo.get_next_sequence(conversation_id)
            await event_repo.add(conversation_id, sequence, event_type, event_data)

            return sequence

    async def add_ledger_snapshot(
        self,
        conversation_id: str,
        task_id: str,
        goal: str,
        status: str,
        snapshot_data: dict[str, Any],
        agent_id: str | None = None,
    ) -> int:
        """Add a ledger snapshot.

        Args:
            conversation_id: Conversation ID
            task_id: Task ID
            goal: Task goal
            status: Task status
            snapshot_data: Full ledger data
            agent_id: Optional agent ID

        Returns:
            Snapshot sequence number
        """
        async with self.db_manager.connection() as db:
            conv_repo = ConversationRepository(db)
            ledger_repo = LedgerRepository(db)

            sequence = await conv_repo.get_next_sequence(conversation_id)
            await ledger_repo.add_snapshot(
                conversation_id=conversation_id,
                sequence=sequence,
                task_id=task_id,
                goal=goal,
                status=status,
                snapshot_data=snapshot_data,
                agent_id=agent_id,
            )

            return sequence

    async def get_conversation_history(
        self, conversation_id: str, include_reasoning: bool = False
    ) -> list[dict[str, Any]]:
        """Get conversation message history.

        Args:
            conversation_id: Conversation ID
            include_reasoning: Whether to include reasoning traces

        Returns:
            List of message dictionaries
        """
        async with self.db_manager.connection() as db:
            message_repo = MessageRepository(db)
            messages = await message_repo.get_history(conversation_id)

            if include_reasoning:
                reasoning_repo = ReasoningRepository(db)
                for msg in messages:
                    trace = await reasoning_repo.get_by_message(msg["id"])
                    if trace:
                        msg["reasoning_trace"] = trace

            return messages

    async def get_ledger_state(self, conversation_id: str) -> list[dict[str, Any]]:
        """Get current ledger state for conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of ledger items
        """
        async with self.db_manager.connection() as db:
            ledger_repo = LedgerRepository(db)
            return await ledger_repo.get_latest(conversation_id)

    async def get_event_history(
        self, conversation_id: str, from_sequence: int | None = None
    ) -> list[dict[str, Any]]:
        """Get event history for replay/resume.

        Args:
            conversation_id: Conversation ID
            from_sequence: Optional starting sequence

        Returns:
            List of event dictionaries
        """
        async with self.db_manager.connection() as db:
            event_repo = EventRepository(db)
            return await event_repo.get_history(conversation_id, from_sequence)
