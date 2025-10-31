"""Regression tests for the conversation store error handling."""

from __future__ import annotations

import pytest

from agentic_fleet.api.conversations.service import ConversationNotFoundError, ConversationStore


def test_create_and_retrieve_conversation() -> None:
    """Ensure newly created conversations can be fetched and listed."""

    store = ConversationStore()
    conversation = store.create(title="Example")

    assert conversation.title == "Example"
    assert store.get(conversation.id) == conversation
    assert store.list() == [conversation]


def test_add_message_round_trip() -> None:
    """Verify messages are appended and retrievable."""

    store = ConversationStore()
    conversation = store.create()

    message = store.add_message(
        conversation_id=conversation.id,
        role="user",
        content="hello world",
    )

    retrieved = store.get(conversation.id)
    assert retrieved.messages[-1] == message
    assert message.content == "hello world"
    assert message.role == "user"


def test_missing_conversation_raises() -> None:
    """Missing conversations should raise the appropriate error."""

    store = ConversationStore()

    with pytest.raises(ConversationNotFoundError):
        store.get("missing")

    with pytest.raises(ConversationNotFoundError):
        store.add_message(conversation_id="missing", role="user", content="nope")
