"""Persistent conversation store for the AgenticFleet API.

This module provides a lightweight JSON-backed store that keeps chat
conversations and messages on disk under ``.var/data`` by default. It uses
Pydantic models from ``schemas.py`` for validation and returns deep copies so
callers can't accidentally mutate in-memory state without persistence.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from agentic_fleet.models import Conversation
from agentic_fleet.utils.cfg import DEFAULT_DATA_DIR

logger = logging.getLogger(__name__)


class ConversationStore:
    """Thread-safe JSON store for conversations."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path(DEFAULT_DATA_DIR) / "conversations.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conversations = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_conversations(self) -> list[Conversation]:
        """Return all conversations sorted by updated_at descending."""
        with self._lock:
            conversations = sorted(
                self._conversations.values(),
                key=lambda c: (c.updated_at or c.created_at),
                reverse=True,
            )
            return [self._clone(c) for c in conversations]

    def get(self, conversation_id: str) -> Conversation | None:
        """Retrieve a conversation by ID or None if not found."""
        with self._lock:
            conversation = self._conversations.get(str(conversation_id))
            return self._clone(conversation) if conversation else None

    def upsert(self, conversation: Conversation) -> Conversation:
        """Insert or update a conversation and persist to disk."""
        with self._lock:
            self._conversations[conversation.id] = conversation
            self._persist()
            return self._clone(conversation)

    def bulk_load(self, conversations: Iterable[Conversation]) -> None:
        """Replace all conversations with the given iterable and persist."""
        with self._lock:
            self._conversations = {c.id: c for c in conversations}
            self._persist()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load(self) -> dict[str, Conversation]:
        if not self.path.exists():
            return {}

        try:
            with self.path.open() as f:
                raw = json.load(f)
        except Exception:
            return {}

        conversations: dict[str, Conversation] = {}
        for item in raw if isinstance(raw, list) else []:
            try:
                conversations[item["id"]] = Conversation.model_validate(item)
            except Exception as e:
                logger.warning(f"Failed to validate conversation item: {e}")
                continue
        return conversations

    def _persist(self) -> None:
        payload = [c.model_dump(mode="json") for c in self._conversations.values()]
        # Ensure deterministic ordering by updated_at desc then created_at
        payload.sort(
            key=lambda c: (
                c.get("updated_at") or c.get("created_at") or datetime.min.isoformat(),
                c.get("id", ""),
            ),
            reverse=True,
        )
        with self.path.open("w") as f:
            json.dump(payload, f, indent=2)

    @staticmethod
    def _clone(conversation: Conversation) -> Conversation:
        return conversation.model_copy(deep=True)


__all__ = ["ConversationStore"]
