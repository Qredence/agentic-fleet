"""Thread-safe in-memory conversation storage for development workflows."""
"""Utilities for storing lightweight conversation history in memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import time
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ConversationRecord:
    """Metadata captured for a conversation."""

    id: str
    created_at: int
    updated_at: int
    metadata: dict[str, str] = field(default_factory=dict)


class InMemoryConversationStore:
    """Simple in-memory conversation storage compatible with the frontend API."""

    def __init__(self) -> None:
        self._conversations: dict[str, ConversationRecord] = {}
        self._items: dict[str, list[dict[str, Any]]] = {}
        self._lock = Lock()
        self._next_id = 1

    def _generate_id(self) -> str:
        conversation_id = f"conv-{self._next_id:06d}"
        self._next_id += 1
        return conversation_id

    @staticmethod
    def _now() -> int:
        return int(time())

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
        if not isinstance(metadata, dict):
            return {}

        sanitized: dict[str, str] = {}
        for key, value in metadata.items():
            key_str = str(key)
            if value is None:
                sanitized[key_str] = ""
            elif isinstance(value, str):
                sanitized[key_str] = value
            else:
                sanitized[key_str] = str(value)
        return sanitized

    def _clone_record(self, record: ConversationRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "metadata": {**record.metadata},
        }

    @staticmethod
    def _clone_item(item: dict[str, Any]) -> dict[str, Any]:
        cloned = {**item}
        content = cloned.get("content")
        if isinstance(content, list):
            cloned["content"] = [block.copy() for block in content if isinstance(block, dict)]
        return cloned

    def create(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        sanitized_metadata = self._sanitize_metadata(metadata)
        conversation_id = self._generate_id()
        timestamp = self._now()
        record = ConversationRecord(
            id=conversation_id,
            created_at=timestamp,
            updated_at=timestamp,
            metadata=sanitized_metadata,
        )

        with self._lock:
            self._conversations[conversation_id] = record
            self._items[conversation_id] = []

        return self._clone_record(record)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        *,
        content: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        sanitized_content: list[dict[str, Any]] = []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    sanitized_content.append(block.copy())
                else:
                    sanitized_content.append({"type": "text", "text": str(block)})

        item = {
            "id": f"item-{uuid4().hex[:12]}",
            "role": role,
            "content": sanitized_content,
            "created_at": self._now(),
        }

        with self._lock:
            conversation = self._conversations.get(conversation_id)
            if conversation is None:
                raise KeyError(conversation_id)
            conversation.updated_at = item["created_at"]
            self._items.setdefault(conversation_id, []).append(item)

        return self._clone_item(item)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            records = [self._clone_record(record) for record in self._conversations.values()]
        return sorted(records, key=lambda record: record["updated_at"], reverse=True)

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._conversations.get(conversation_id)
            if record is None:
                return None
            return self._clone_record(record)

    def delete(self, conversation_id: str) -> bool:
        with self._lock:
            conversation_removed = self._conversations.pop(conversation_id, None)
            self._items.pop(conversation_id, None)
        return conversation_removed is not None

    def list_items(self, conversation_id: str) -> list[dict[str, Any]] | None:
        with self._lock:
            if conversation_id not in self._conversations:
                return None
            items = self._items.get(conversation_id, [])
            return [self._clone_item(item) for item in items]
