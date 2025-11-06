"""Adapter to bridge between persistence service and conversation API."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from openai import AsyncOpenAI

from agentic_fleet.api.conversations.service import (
    Conversation,
    ConversationMessage,
    ConversationStore,
    MessageRole,
)
from agentic_fleet.persistence import (
    ConversationPersistenceService,
    DatabaseManager,
    get_persistence_settings,
)

logger = logging.getLogger(__name__)


class PersistenceAdapter:
    """Adapter that provides ConversationStore interface backed by SQLite persistence."""

    def __init__(
        self,
        persistence_service: ConversationPersistenceService,
        fallback_store: ConversationStore | None = None,
    ) -> None:
        """Initialize persistence adapter.

        Args:
            persistence_service: SQLite persistence service
            fallback_store: Optional in-memory store for fallback when persistence disabled
        """
        self._persistence = persistence_service
        self._fallback = fallback_store

    async def create(self, title: str | None = None) -> Conversation:
        """Create a new conversation.

        Args:
            title: Conversation title

        Returns:
            Created conversation
        """
        workflow_id = "magentic_fleet"  # Default workflow
        conv_id = await self._persistence.create_conversation(
            workflow_id=workflow_id, metadata={"title": title or "Untitled"}
        )

        return Conversation(
            id=conv_id,
            title=title or "Untitled",
            created_at=int(__import__("time").time()),
            messages=[],
        )

    async def list(self) -> list[Conversation]:
        """List all conversations.

        Returns:
            List of conversations ordered by most recent first
        """
        from agentic_fleet.persistence.repositories import ConversationRepository

        async with self._persistence.db_manager.connection() as db:
            conv_repo = ConversationRepository(db)
            conversation_records = await conv_repo.list_all()

        # Convert to Conversation objects
        conversations = []
        for record in conversation_records:
            metadata = (
                __import__("json").loads(record.get("metadata_json", "{}"))
                if record.get("metadata_json")
                else {}
            )
            title = metadata.get("title", "Untitled")
            created_at = int(record.get("created_at", __import__("time").time()))

            # Note: We don't load messages for list operations (performance)
            conversations.append(
                Conversation(
                    id=record["id"],
                    title=title,
                    created_at=created_at,
                    messages=[],
                )
            )

        return conversations

    async def get(self, conversation_id: str) -> Conversation:
        """Get a conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation with message history

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        from agentic_fleet.api.conversations.service import ConversationNotFoundError
        from agentic_fleet.persistence.repositories import ConversationRepository

        # First check if conversation exists in database
        async with self._persistence.db_manager.connection() as db:
            conv_repo = ConversationRepository(db)
            conversation_record = await conv_repo.get(conversation_id)

        if not conversation_record:
            raise ConversationNotFoundError(conversation_id)

        # Get conversation history from persistence (may be empty for new conversations)
        history = await self._persistence.get_conversation_history(
            conversation_id, include_reasoning=True
        )

        # Convert persistence messages to ConversationMessage format
        messages = [
            ConversationMessage(
                id=msg.get("id", ""),
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                created_at=int(msg.get("created_at", 0)),
                reasoning=msg.get("reasoning"),
            )
            for msg in history
        ]

        # Get metadata from conversation record
        metadata = (
            __import__("json").loads(conversation_record.get("metadata_json", "{}"))
            if conversation_record.get("metadata_json")
            else {}
        )
        title = metadata.get("title", "Conversation")
        created_at = int(conversation_record.get("created_at", __import__("time").time()))

        return Conversation(
            id=conversation_id,
            title=title,
            created_at=created_at,
            messages=messages,
        )

    async def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        reasoning: str | None = None,
    ) -> ConversationMessage:
        """Add a message to conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant/system)
            content: Message content
            reasoning: Optional reasoning trace

        Returns:
            Created message
        """
        message = await self._persistence.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            reasoning=reasoning,
        )

        return ConversationMessage(
            id=message.get("id", ""),
            role=message.get("role", "user"),
            content=message.get("content", ""),
            created_at=int(message.get("created_at", 0)),
            reasoning=message.get("reasoning"),
        )

    async def get_formatted_history(self, conversation_id: str, max_messages: int = 10) -> str:
        """Get formatted conversation history for agent context.

        Args:
            conversation_id: Conversation ID
            max_messages: Maximum number of recent messages to include

        Returns:
            Formatted conversation history string
        """
        history = await self._persistence.get_conversation_history(
            conversation_id, include_reasoning=False
        )

        if not history:
            return ""

        # Take last N messages
        recent_messages = history[-max_messages:] if len(history) > max_messages else history

        # Format as "ROLE: content"
        formatted = []
        for msg in recent_messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")

        return "\n\n".join(formatted)


def create_persistence_adapter() -> PersistenceAdapter:
    """Create persistence adapter with proper initialization.

    Returns:
        Initialized persistence adapter
    """
    settings = get_persistence_settings()

    if not settings.enabled:
        logger.info("[PERSISTENCE] Persistence disabled, using in-memory store only")
        from agentic_fleet.api.conversations.service import get_store

        return PersistenceAdapter(
            persistence_service=None,  # type: ignore
            fallback_store=get_store(),
        )

    # Initialize database manager
    db_path = Path(settings.db_path)
    db_manager = DatabaseManager(db_path, init_schema=True)

    # Initialize OpenAI client for summarization if API key available
    openai_client = None
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = AsyncOpenAI(api_key=api_key)
        logger.info("[PERSISTENCE] OpenAI client initialized for summarization")
    else:
        logger.warning("[PERSISTENCE] No OPENAI_API_KEY found, summarization will use fallback")

    # Create persistence service
    persistence_service = ConversationPersistenceService(
        db_manager=db_manager,
        settings=settings,
        openai_client=openai_client,
    )

    logger.info(
        f"[PERSISTENCE] SQLite persistence enabled at {db_path}, "
        f"summary_threshold={settings.summary_threshold}"
    )

    return PersistenceAdapter(persistence_service=persistence_service)


# Singleton instance
_adapter: PersistenceAdapter | None = None


def get_persistence_adapter() -> PersistenceAdapter:
    """Get or create the singleton persistence adapter.

    Returns:
        Persistence adapter instance
    """
    global _adapter
    if _adapter is None:
        _adapter = create_persistence_adapter()
    return _adapter
