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
        """List all stored conversations."""
        # Access internal cache directly for iteration (SyncTTLCache uses OrderedDict)
        # Note: This relies on internal implementation detail but acceptable for utilities.
        # Alternatively SyncTTLCache should expose values()
        # Using private _cache attribute of SyncTTLCache
        return [
            entry.value
            for entry in self._cache._cache.values()
            if isinstance(entry.value, Conversation)
        ]

    def delete(self, conversation_id: str) -> None:
        """Delete a conversation."""
        self._cache.invalidate(conversation_id)
