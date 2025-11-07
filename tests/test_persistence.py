"""Tests for SQLite persistence layer."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from agentic_fleet.persistence import (
    ConversationPersistenceService,
    ConversationRepository,
    DatabaseManager,
    MessageRepository,
    PersistenceSettings,
    ReasoningRepository,
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
    """Factory fixture to create persistence service with customizable settings."""

    def _factory(summary_threshold=10, summary_keep_recent=None):
        settings = PersistenceSettings()
        settings.enabled = True
        settings.summary_threshold = summary_threshold
        if summary_keep_recent is not None:
            settings.summary_keep_recent = summary_keep_recent
        return ConversationPersistenceService(db_manager, settings)

    return _factory


@pytest.mark.asyncio
async def test_create_conversation(persistence_service):
    """Test conversation creation."""
    svc = persistence_service()
    conv_id = await svc.create_conversation(
        workflow_id="test-workflow",
        metadata={"test": "data"},
    )

    assert conv_id is not None
    assert len(conv_id) > 0


@pytest.mark.asyncio
async def test_add_message_with_sequence(persistence_service):
    """Test adding message with automatic sequencing."""
    svc = persistence_service()
    conv_id = await svc.create_conversation(workflow_id="test-workflow")

    # Add first message
    msg1 = await svc.add_message(
        conversation_id=conv_id,
        role="user",
        content="Hello",
    )
    assert msg1["sequence"] == 0

    # Add second message
    msg2 = await svc.add_message(
        conversation_id=conv_id,
        role="assistant",
        content="Hi there",
        reasoning="Responding to greeting",
    )
    assert msg2["sequence"] == 1
    assert msg2["reasoning"] == "Responding to greeting"


@pytest.mark.asyncio
async def test_sequence_monotonic_increment(db_manager):
    """Test that sequences increment monotonically."""
    conv_id = "test-conv"

    async with db_manager.connection() as db:
        conv_repo = ConversationRepository(db)
        await conv_repo.create(conv_id, "test-workflow")

        # Get multiple sequences
        sequences = []
        for _ in range(10):
            seq = await conv_repo.get_next_sequence(conv_id)
            sequences.append(seq)

        # Verify monotonic increment
        assert sequences == list(range(10))


@pytest.mark.asyncio
async def test_concurrent_sequence_allocation(db_manager):
    """Test that concurrent sequence allocation remains monotonic."""
    conv_id = "test-conv"

    async with db_manager.connection() as db:
        conv_repo = ConversationRepository(db)
        await conv_repo.create(conv_id, "test-workflow")

    # Allocate sequences concurrently
    async def get_seq():
        async with db_manager.connection() as db:
            conv_repo = ConversationRepository(db)
            return await conv_repo.get_next_sequence(conv_id)

    sequences = await asyncio.gather(*[get_seq() for _ in range(20)])

    # Verify all unique and in range
    assert len(set(sequences)) == 20
    assert min(sequences) == 0
    assert max(sequences) == 19


@pytest.mark.asyncio
async def test_message_history_ordering(persistence_service):
    """Test that message history maintains sequence order."""
    svc = persistence_service()
    conv_id = await svc.create_conversation(workflow_id="test-workflow")

    # Add messages
    for i in range(5):
        await svc.add_message(
            conversation_id=conv_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
        )

    # Get history
    history = await svc.get_conversation_history(conv_id)

    # Verify order
    assert len(history) == 5
    for i, msg in enumerate(history):
        assert msg["sequence"] == i
        assert msg["content"] == f"Message {i}"


@pytest.mark.asyncio
async def test_ledger_snapshot(persistence_service):
    """Test ledger snapshot storage."""
    svc = persistence_service()
    conv_id = await svc.create_conversation(workflow_id="test-workflow")

    # Add ledger snapshots
    await svc.add_ledger_snapshot(
        conversation_id=conv_id,
        task_id="task-1",
        goal="Complete task 1",
        status="in_progress",
        snapshot_data={"progress": 50},
    )

    await svc.add_ledger_snapshot(
        conversation_id=conv_id,
        task_id="task-1",
        goal="Complete task 1",
        status="completed",
        snapshot_data={"progress": 100},
    )

    # Get latest state
    ledger = await svc.get_ledger_state(conv_id)

    # Should only get latest snapshot per task
    assert len(ledger) == 1
    assert ledger[0]["status"] == "completed"
    assert ledger[0]["task_id"] == "task-1"


@pytest.mark.asyncio
async def test_event_storage(persistence_service):
    """Test event storage with sequencing."""
    svc = persistence_service()
    conv_id = await svc.create_conversation(workflow_id="test-workflow")

    # Add events
    seq1 = await svc.add_event(
        conversation_id=conv_id,
        event_type="workflow.start",
        event_data={"workflow_id": "test"},
    )

    seq2 = await svc.add_event(
        conversation_id=conv_id,
        event_type="agent.message",
        event_data={"agent": "planner"},
    )

    # Verify sequencing
    assert seq1 == 0
    assert seq2 == 1

    # Get event history
    events = await svc.get_event_history(conv_id)
    assert len(events) == 2
    assert events[0]["event_type"] == "workflow.start"
    assert events[1]["event_type"] == "agent.message"


@pytest.mark.asyncio
async def test_reasoning_trace_storage(persistence_service):
    """Test reasoning trace storage separate from messages."""
    svc = persistence_service()
    conv_id = await svc.create_conversation(workflow_id="test-workflow")

    # Add message with reasoning
    await svc.add_message(
        conversation_id=conv_id,
        role="assistant",
        content="Answer",
        reasoning="Detailed reasoning trace",
    )

    # Get history with reasoning
    history = await svc.get_conversation_history(conv_id, include_reasoning=True)

    assert len(history) == 1
    assert history[0]["reasoning"] == "Detailed reasoning trace"
    assert "reasoning_trace" in history[0]


@pytest.mark.asyncio
async def test_summarization_threshold(persistence_service):
    """Test automatic summarization at threshold."""
    # Use custom configuration via factory, do not mutate internals directly
    svc = persistence_service(summary_threshold=8, summary_keep_recent=2)

    conv_id = await svc.create_conversation(workflow_id="test-workflow")

    # Add messages beyond threshold to trigger summarization (10 > 8)
    for i in range(10):
        await svc.add_message(
            conversation_id=conv_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
        )

    # Get history - should have summary + recent messages
    history = await svc.get_conversation_history(conv_id)

    # Should have triggered summarization: summary message + 2 recent messages = 3
    # (8 messages summarized, keeping last 2)
    assert len(history) == 3  # Summary + 2 recent messages

    # Check if a summary message exists
    # Prefer robust field checks: 'type' or 'is_summary' if they exist, fallback to strict matching
    summary_messages = [
        m
        for m in history
        if m["role"] == "system"
        and (
            m.get("type") == "summary"
            or m.get("is_summary") is True
            or m["content"].lower().startswith("summary:")
        )
    ]
    assert len(summary_messages) >= 1, "Expected at least one summary message"


@pytest.mark.asyncio
async def test_event_replay(persistence_service):
    """Test event replay from specific sequence."""
    svc = persistence_service()
    conv_id = await svc.create_conversation(workflow_id="test-workflow")

    # Add events
    for i in range(5):
        await svc.add_event(
            conversation_id=conv_id,
            event_type=f"event-{i}",
            event_data={"index": i},
        )

    # Replay from sequence 2
    events = await svc.get_event_history(conv_id, from_sequence=2)

    assert len(events) == 3
    assert events[0]["event_type"] == "event-2"
    assert events[-1]["event_type"] == "event-4"


@pytest.mark.asyncio
async def test_reasoning_repository(db_manager):
    """Test reasoning repository operations."""
    conv_id = "test-conv"
    msg_id = "test-msg"

    async with db_manager.connection() as db:
        conv_repo = ConversationRepository(db)
        msg_repo = MessageRepository(db)
        reasoning_repo = ReasoningRepository(db)

        # Create conversation and message
        await conv_repo.create(conv_id, "test-workflow")
        seq = await conv_repo.get_next_sequence(conv_id)
        await msg_repo.add(
            message_id=msg_id,
            conversation_id=conv_id,
            sequence=seq,
            role="assistant",
            content="Answer",
        )

        # Add reasoning trace
        await reasoning_repo.add(
            conversation_id=conv_id,
            message_id=msg_id,
            reasoning_text="Detailed trace",
            effort="high",
            verbosity="verbose",
            model="test-model",
            metadata={"tokens": 1000},
        )

        # Retrieve by message
        trace = await reasoning_repo.get_by_message(msg_id)
        assert trace is not None
        assert trace["reasoning_text"] == "Detailed trace"
        assert trace["effort"] == "high"
        assert trace["model"] == "test-model"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
