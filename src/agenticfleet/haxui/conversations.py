from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .models import (
    ConversationItem,
    ConversationItemsResponse,
    ConversationListResponse,
    ConversationSummary,
)
from .storage import SQLiteConversationStore


@dataclass(slots=True)
class ConversationRecord:
    summary: ConversationSummary
    items: list[ConversationItem] = field(default_factory=list)


class ConversationStore:
    """In-memory conversation tracker implementing an OpenAI-compatible surface."""

    def __init__(self, persistence: SQLiteConversationStore | None = None) -> None:
        self._records: dict[str, ConversationRecord] = {}
        self._lock = asyncio.Lock()
        self._persistence = persistence

    async def create(self, metadata: dict[str, str] | None = None) -> ConversationSummary:
        async with self._lock:
            conversation_id = f"conv_{uuid4().hex[:12]}"
            summary = ConversationSummary(id=conversation_id, metadata=metadata)
            self._records[conversation_id] = ConversationRecord(summary=summary)

        if self._persistence is not None:
            await self._persistence.create(summary)

        return summary

    async def list(self) -> ConversationListResponse:
        async with self._lock:
            cached = list(self._records.values())

        if self._persistence is not None:
            return await self._persistence.list_conversations()

        return ConversationListResponse(data=[record.summary for record in cached])

    async def get(self, conversation_id: str) -> ConversationSummary:
        async with self._lock:
            record = self._records.get(conversation_id)
            if record is None:
                if self._persistence is None:
                    raise KeyError(conversation_id)
                summary = await self._persistence.fetch_conversation(conversation_id)
                if summary is None:
                    raise KeyError(conversation_id)
                # Repopulate cache for faster subsequent access
                self._records[conversation_id] = ConversationRecord(summary=summary)
                return summary
            return record.summary

    async def delete(self, conversation_id: str) -> None:
        async with self._lock:
            self._records.pop(conversation_id, None)
        if self._persistence is not None:
            await self._persistence.delete(conversation_id)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: list[dict[str, Any]],  # type: ignore[valid-type]
        *,
        status: str = "completed",
    ) -> ConversationItem:
        async with self._lock:
            record = self._records.get(conversation_id)
            if record is None:
                if self._persistence is None:
                    raise KeyError(conversation_id)
                summary = await self._persistence.fetch_conversation(conversation_id)
                if summary is None:
                    raise KeyError(conversation_id)
                record = ConversationRecord(summary=summary)
                self._records[conversation_id] = record
            item = ConversationItem(
                id=f"msg_{uuid4().hex[:12]}",
                role=role,  # type: ignore[arg-type]
                content=content,
                type="message",
                status=status,  # type: ignore[arg-type]
            )
            record.items.append(item)

        if self._persistence is not None:
            await self._persistence.upsert_message(
                message=item,
                conversation_id=conversation_id,
            )

        return item

    async def list_items(self, conversation_id: str) -> ConversationItemsResponse:
        if self._persistence is not None:
            response = await self._persistence.list_items(conversation_id)
            async with self._lock:
                record = self._records.get(conversation_id)
                if record is not None:
                    record.items = list(response.data)
            return response

        async with self._lock:
            record = self._records.get(conversation_id)
            if record is None:
                raise KeyError(conversation_id)
            return ConversationItemsResponse(data=list(record.items))
