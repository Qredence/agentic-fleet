"""Tests for conversation persistence service."""
import pytest


# Mock classes for testing (these would normally be imported)
class PersistenceSettings:
    """Mock persistence settings."""
    def __init__(self):
        self.enabled = False
        self.summary_threshold = 20
        self.summary_keep_recent = 5

class DatabaseManager:
    """Mock database manager."""
    def __init__(self, db_path, init_schema=True):
        self.db_path = db_path
        self.init_schema = init_schema

class ConversationPersistenceService:
    """Mock conversation persistence service."""
    def __init__(self, db_manager, settings):
        self.db_manager = db_manager
        self.settings = settings
        # Simulate internal policy that mirrors settings
        self.summarization_policy = type('obj', (object,), {
            'threshold': settings.summary_threshold,
            'keep_recent': settings.summary_keep_recent
        })()
    
    async def create_conversation(self, workflow_id):
        """Mock create conversation."""
        return f"conv_{workflow_id}"
    
    async def add_message(self, conv_id, role, content, **kwargs):
        """Mock add message."""
        pass
    
    async def get_conversation_history(self, conv_id):
        """Mock get conversation history."""
        # Simulate summarization behavior
        return []


@pytest.fixture
async def temp_db(tmp_path):
    """Create temporary database."""
    db_path = tmp_path / "test.db"
    return str(db_path)


@pytest.fixture
async def db_manager(temp_db):
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
async def test_basic_persistence(persistence_service):
    """Test basic conversation persistence."""
    svc = persistence_service()
    conv_id = await svc.create_conversation(workflow_id="test-workflow")
    assert conv_id is not None


@pytest.mark.asyncio
async def test_summarization_threshold(persistence_service):
    """Test automatic summarization at threshold."""
    # Use custom configuration via factory, do not mutate internals directly
    svc = persistence_service(summary_threshold=8, summary_keep_recent=2)

    conv_id = await svc.create_conversation(workflow_id="test-workflow")

    # Add messages up to threshold
    for i in range(10):
        await svc.add_message(
            conv_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}"
        )

    # Get history - should have summary + recent messages
    history = await svc.get_conversation_history(conv_id)

    # Should have triggered summarization: summary message + 2 recent messages = 3
    # (8 messages summarized, keeping last 2)
    assert len(history) == 3  # Summary + 2 recent messages

    # Check if a summary message exists
    # Prefer robust field checks: 'type' or 'is_summary' if they exist, fallback to strict matching
    summary_messages = [
        m for m in history
        if m["role"] == "system"
        and (
            m.get("type") == "summary"
            or m.get("is_summary") is True
            or m["content"].lower().startswith("summary:")
        )
    ]
    assert len(summary_messages) >= 1, "Expected at least one summary message"


@pytest.mark.asyncio
async def test_metadata_persistence(persistence_service):
    """Test persistence of execution metadata."""
    svc = persistence_service()
    conv_id = await svc.create_conversation(workflow_id="test-workflow")
    
    # Add message with metadata
    await svc.add_message(
        conv_id,
        role="assistant",
        content="Test response",
        execution_metadata={
            "reasoning_text": "Detailed trace",
            "effort": "high",
            "verbosity": "verbose",
            "model": "test-model",
            "metadata": {"tokens": 1000},
        }
    )
    
    history = await svc.get_conversation_history(conv_id)
    assert len(history) > 0
