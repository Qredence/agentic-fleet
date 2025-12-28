"""Conversation storage backend."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from agentic_fleet.models import Conversation
from agentic_fleet.utils.ttl_cache import TTLCache

if TYPE_CHECKING:
    from agentic_fleet.models import Conversation

logger = logging.getLogger(__name__)


class ConversationStore:
    """Stores conversation history logic.

    Uses an in-memory TTL cache backed by local JSON file storage.
    Conversations are automatically loaded from disk on initialization
    and saved to disk on every update.
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
            # Load conversations from disk on initialization
            self._load_from_disk()

    def upsert(self, conversation: Conversation) -> Conversation:
        """Create or update a conversation."""
        conversation_key = getattr(conversation, "conversation_id", getattr(conversation, "id"))
        self._cache.set(conversation_key, conversation)
        # Persist to disk if storage path is configured
        if self.storage_path:
            self._save_to_disk()
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
        # Persist to disk if storage path is configured
        if self.storage_path:
            self._save_to_disk()

    def _load_from_disk(self) -> None:
        """Load conversations from disk into the cache."""
        if not self.storage_path:
            return

        storage_file = Path(self.storage_path)
        if not storage_file.exists():
            logger.debug(f"Conversation storage file does not exist: {self.storage_path}")
            return

        try:
            with open(storage_file) as f:
                data = json.load(f)

            # Handle both array and dict formats for backward compatibility
            if isinstance(data, list):
                conversations_data = data
            elif isinstance(data, dict) and "conversations" in data:
                conversations_data = data["conversations"]
            else:
                logger.warning(f"Unexpected conversation file format: {storage_file}")
                return

            loaded_count = 0
            for conv_data in conversations_data:
                try:
                    # Handle both 'id' and 'conversation_id' for migration
                    if "conversation_id" in conv_data:
                        pass
                    elif "id" in conv_data:
                        # Migrate to conversation_id
                        conv_data["conversation_id"] = conv_data["id"]
                        del conv_data["id"]
                    else:
                        logger.warning("Conversation missing ID field, skipping")
                        continue

                    conversation = Conversation.model_validate(conv_data)
                    self._cache.set(conversation.conversation_id, conversation)
                    loaded_count += 1
                except Exception as e:
                    logger.warning(f"Failed to load conversation: {e}", exc_info=True)
                    continue

            logger.info(f"Loaded {loaded_count} conversations from {storage_file}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse conversation file {storage_file}: {e}")
        except Exception as e:
            logger.warning(f"Failed to load conversations from {storage_file}: {e}", exc_info=True)

    def _save_to_disk(self) -> None:
        """Save all conversations to disk using atomic write pattern."""
        if not self.storage_path:
            return

        storage_file = Path(self.storage_path)
        storage_file.parent.mkdir(parents=True, exist_ok=True)

        # Get all conversations from cache
        conversations = self.list_conversations()

        try:
            # Write to temporary file first (atomic write pattern)
            temp_file = storage_file.with_suffix(storage_file.suffix + ".tmp")
            with open(temp_file, "w") as f:
                json.dump(
                    [conv.model_dump(mode="json") for conv in conversations],
                    f,
                    indent=2,
                    default=str,  # Handle datetime serialization
                )

            # Atomic replace
            temp_file.replace(storage_file)
            logger.debug(f"Saved {len(conversations)} conversations to {storage_file}")
        except Exception as e:
            logger.warning(f"Failed to save conversations to {storage_file}: {e}", exc_info=True)
            # Clean up temp file on error
            temp_file = storage_file.with_suffix(storage_file.suffix + ".tmp")
            if temp_file.exists():
                from contextlib import suppress

                with suppress(Exception):
                    temp_file.unlink()
