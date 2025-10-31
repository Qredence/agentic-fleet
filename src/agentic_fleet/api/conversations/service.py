from __future__ import annotations

import builtins
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

MessageRole = Literal["user", "assistant", "system"]


@dataclass(slots=True)
class ConversationMessage:
    id: str
    role: MessageRole
    content: str
    created_at: int = field(default_factory=lambda: int(time.time()))


@dataclass(slots=True)
class Conversation:
    id: str
    title: str
    created_at: int
    messages: list[ConversationMessage] = field(default_factory=list)


class ConversationNotFoundError(KeyError):
    """Raised when a conversation cannot be located."""


class ConversationStore:
    """In-memory storage for chat conversations."""

    def __init__(self) -> None:
        self._items: dict[str, Conversation] = {}

    def create(self, title: str | None = None) -> Conversation:
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            title=title or "Untitled",
            created_at=int(time.time()),
        )
        self._items[conversation_id] = conversation
        return conversation

    def list(self) -> builtins.list[Conversation]:
        return list(self._items.values())

    def get(self, conversation_id: str) -> Conversation:
        try:
            return self._items[conversation_id]
        except KeyError as exc:
            raise ConversationNotFoundError(conversation_id) from exc

    def add_message(
        self, conversation_id: str, role: MessageRole, content: str
    ) -> ConversationMessage:
        conversation = self.get(conversation_id)
        message = ConversationMessage(id=str(uuid.uuid4()), role=role, content=content)
        conversation.messages.append(message)
        return message


_store = ConversationStore()


def get_store() -> ConversationStore:
    """Return the singleton conversation store."""

    return _store
