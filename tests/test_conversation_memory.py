"""Tests for conversation memory and context retention."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from agentic_fleet.api.conversations.persistence_adapter import PersistenceAdapter
from agentic_fleet.persistence import (
    ConversationPersistenceService,
    DatabaseManager,
    PersistenceSettings,
    init_database,
)


@pytest_asyncio.fixture
async def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)
        yield db_path


@pytest.fixture
def db_manager(temp_db):
    """Create database manager."""
    return DatabaseManager(temp_db, init_schema=False)


@pytest.fixture
def persistence_service(db_manager):
    """Create persistence service."""
    settings = PersistenceSettings()
    settings.enabled = True
    settings.summary_threshold = 20  # Higher threshold for testing
    return ConversationPersistenceService(db_manager, settings)


@pytest.fixture
def persistence_adapter(persistence_service):
    """Create persistence adapter."""
    return PersistenceAdapter(persistence_service=persistence_service)


@pytest.mark.asyncio
async def test_conversation_memory_retention(persistence_adapter):
    """Test that conversations retain history across messages."""
    # Create a conversation
    conversation = await persistence_adapter.create(title="Test Conversation")
    conv_id = conversation.id

    # Add first user message and assistant response
    await persistence_adapter.add_message(
        conv_id, role="user", content="What is the capital of France?"
    )
    await persistence_adapter.add_message(
        conv_id, role="assistant", content="The capital of France is Paris."
    )

    # Add follow-up message (should have context from previous exchange)
    await persistence_adapter.add_message(conv_id, role="user", content="What is its population?")

    # Get formatted history
    history = await persistence_adapter.get_formatted_history(conv_id, max_messages=10)

    # Verify history contains all previous messages
    assert "What is the capital of France?" in history
    assert "The capital of France is Paris" in history
    assert "What is its population?" in history

    # Verify messages are in correct order
    assert history.index("What is the capital of France?") < history.index(
        "The capital of France is Paris."
    )
    assert history.index("The capital of France is Paris.") < history.index(
        "What is its population?"
    )


@pytest.mark.asyncio
async def test_conversation_history_formatting(persistence_adapter):
    """Test that conversation history is properly formatted for agent context."""
    conversation = await persistence_adapter.create()
    conv_id = conversation.id

    # Add several messages
    await persistence_adapter.add_message(conv_id, role="user", content="Hello")
    await persistence_adapter.add_message(conv_id, role="assistant", content="Hi there!")
    await persistence_adapter.add_message(conv_id, role="user", content="Tell me a joke")
    await persistence_adapter.add_message(
        conv_id,
        role="assistant",
        content="Why did the chicken cross the road? To get to the other side!",
    )

    # Get formatted history
    history = await persistence_adapter.get_formatted_history(conv_id)

    # Verify format: "ROLE: content" with double newlines
    assert "USER: Hello" in history
    assert "ASSISTANT: Hi there!" in history
    assert "USER: Tell me a joke" in history
    assert "ASSISTANT: Why did the chicken" in history

    # Verify messages are separated
    lines = history.split("\n\n")
    assert len(lines) == 4  # 4 messages


@pytest.mark.asyncio
async def test_conversation_history_window(persistence_adapter):
    """Test that history window limits number of messages."""
    conversation = await persistence_adapter.create()
    conv_id = conversation.id

    # Add 15 messages
    for i in range(15):
        await persistence_adapter.add_message(
            conv_id, role="user" if i % 2 == 0 else "assistant", content=f"Message {i}"
        )

    # Get history with max 5 messages
    history = await persistence_adapter.get_formatted_history(conv_id, max_messages=5)

    # Verify only last 5 messages are included
    assert "Message 10" in history  # Last 5: 10, 11, 12, 13, 14
    assert "Message 11" in history
    assert "Message 12" in history
    assert "Message 13" in history
    assert "Message 14" in history

    # Verify earlier messages are not included
    assert "Message 0" not in history
    assert "Message 5" not in history
    assert "Message 9" not in history


@pytest.mark.asyncio
async def test_empty_conversation_history(persistence_adapter):
    """Test that empty conversations return empty history."""
    conversation = await persistence_adapter.create()
    conv_id = conversation.id

    # Get history of empty conversation
    history = await persistence_adapter.get_formatted_history(conv_id)

    # Should be empty string
    assert history == ""


@pytest.mark.asyncio
async def test_empty_conversation_retrieval(persistence_adapter):
    """Test that newly created conversations can be retrieved before adding messages."""
    # This was the bug: get() would fail for conversations with no messages
    conversation = await persistence_adapter.create(title="New Conversation")
    conv_id = conversation.id

    # Should be able to retrieve conversation even with no messages
    retrieved = await persistence_adapter.get(conv_id)

    # Verify conversation exists and has no messages
    assert retrieved.id == conv_id
    assert retrieved.title == "New Conversation"
    assert len(retrieved.messages) == 0


@pytest.mark.asyncio
async def test_conversation_retrieval_with_history(persistence_adapter):
    """Test that retrieving a conversation includes full message history."""
    conversation = await persistence_adapter.create(title="Test")
    conv_id = conversation.id

    # Add messages
    await persistence_adapter.add_message(conv_id, role="user", content="First")
    await persistence_adapter.add_message(conv_id, role="assistant", content="Second")
    await persistence_adapter.add_message(conv_id, role="user", content="Third")

    # Retrieve conversation
    retrieved = await persistence_adapter.get(conv_id)

    # Verify all messages are included
    assert len(retrieved.messages) == 3
    assert retrieved.messages[0].content == "First"
    assert retrieved.messages[1].content == "Second"
    assert retrieved.messages[2].content == "Third"

    # Verify order is preserved
    assert retrieved.messages[0].role == "user"
    assert retrieved.messages[1].role == "assistant"
    assert retrieved.messages[2].role == "user"
