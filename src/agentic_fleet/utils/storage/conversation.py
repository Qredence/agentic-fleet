"""Conversation storage backend."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agentic_fleet.models import Conversation
from agentic_fleet.utils.ttl_cache import TTLCache

if TYPE_CHECKING:
    from agentic_fleet.models import Conversation

logger = logging.getLogger(__name__)


class ConversationStore:
    """Stores conversation history logic.

    Currently uses an in-memory TTL cache, but designed to be backed
    by Cosmos DB or file storage.
    """

    def __init__(
        self,
        storage_path: str | None = None,
        ttl_seconds: int = 3600 * 24,
        max_size: int = 1000,
    ) -> None:
        self.storage_path = storage_path
        self._cache = TTLCache(max_size=max_size, ttl_seconds=ttl_seconds)
        if storage_path:
            logger.debug(f"Initializing ConversationStore with path: {storage_path}")
            # Placeholder for disk loading logic if needed in Phase 4

    def upsert(self, conversation: Conversation) -> Conversation:
        """Create or update a conversation."""
        self._cache.set(conversation.id, conversation)
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        return self._cache.get(conversation_id)

    def list_conversations(self) -> list[Conversation]:
        """
        Return all Conversation objects currently stored in the backend.
        
        Returns:
            list[Conversation]: A list of Conversation instances present in storage.
        """
        # Use the public values() interface of TTLCache to retrieve all conversations
        conversations: list[Conversation] = []
        for value in self._cache.values():
            if isinstance(value, Conversation):
                conversations.append(value)
        return conversations

    def delete(self, conversation_id: str) -> None:
        """
        Remove the conversation with the given ID from storage.
        
        Parameters:
            conversation_id (str): Identifier of the conversation to remove.
        """
        self._cache.invalidate(conversation_id)