"""Conversation persistence utilities.

This module provides lightweight persistence settings and an in-memory
conversation persistence service suitable for tests and local execution.

"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any


@dataclass
class PersistenceSettings:
    """Settings controlling conversation persistence behaviors."""

    enabled: bool = False
    summary_threshold: int = 20
    summary_keep_recent: int = 5


class DatabaseManager:
    """Placeholder database manager used for dependency injection."""

    def __init__(self, db_path: str, init_schema: bool = True):
        self.db_path = db_path
        self.init_schema = init_schema


class ConversationPersistenceService:
    """Simple in-memory conversation persistence implementation."""

    def __init__(self, db_manager: DatabaseManager, settings: PersistenceSettings):
        self.db_manager = db_manager
        self.settings = settings
        self.summarization_policy = SimpleNamespace(
            threshold=settings.summary_threshold,
            keep_recent=settings.summary_keep_recent,
        )
        self._conversations: dict[str, list[dict[str, Any]]] = {}

    async def create_conversation(self, workflow_id: str) -> str:
        """Create a new conversation entry and return its identifier."""
        conv_id = f"conv_{workflow_id}"
        self._conversations.setdefault(conv_id, [])
        return conv_id

    async def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        execution_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to a conversation, capturing optional metadata."""
        history = self._conversations.setdefault(conv_id, [])
        history.append(
            {
                "role": role,
                "content": content,
                "execution_metadata": execution_metadata or {},
            }
        )
        await self._apply_summarization(conv_id)

    async def get_conversation_history(self, conv_id: str) -> list[dict[str, Any]]:
        """Return a shallow copy of the conversation history."""
        history = self._conversations.get(conv_id, [])
        return [entry.copy() for entry in history]

    async def _apply_summarization(self, conv_id: str) -> None:
        """Apply summarization based on configured thresholds."""
        if not self.settings.enabled:
            return

        threshold = max(0, int(self.summarization_policy.threshold or 0))
        keep_recent = max(0, int(self.summarization_policy.keep_recent or 0))
        if threshold <= 0:
            return

        history = self._conversations.get(conv_id, [])
        non_summary_messages = [m for m in history if not m.get("is_summary")]
        if len(non_summary_messages) <= threshold:
            return

        if keep_recent >= len(non_summary_messages):
            # Nothing to summarize yet
            return

        cutoff = len(non_summary_messages) - keep_recent
        to_summarize = non_summary_messages[:cutoff]
        recent = non_summary_messages[cutoff:]

        summary_text = "Summary: " + " ".join(msg["content"] for msg in to_summarize)
        summary_message = {
            "role": "system",
            "content": summary_text.strip(),
            "is_summary": True,
            "type": "summary",
        }

        self._conversations[conv_id] = [summary_message] + [msg.copy() for msg in recent]
