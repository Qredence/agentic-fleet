from datetime import datetime, timedelta

from agentic_fleet.models import Conversation, Message, MessageRole
from agentic_fleet.utils.storage.conversation import ConversationStore


def test_conversation_store_upsert_and_get(tmp_path):
    """Test that ConversationStore can upsert and retrieve conversations."""
    path = tmp_path / "conversations.json"
    store = ConversationStore(str(path))

    convo = Conversation(id="c1", title="Test Chat")
    msg = Message(role=MessageRole.USER, content="hello", author="User")
    convo.messages.append(msg)
    store.upsert(convo)

    # Same store instance should retrieve the conversation
    retrieved = store.get("c1")

    assert retrieved is not None
    assert retrieved.title == "Test Chat"
    assert len(retrieved.messages) == 1
    assert retrieved.messages[0].author == "User"


def test_store_list_conversations(tmp_path):
    """Test listing all conversations from the store."""
    path = tmp_path / "conversations.json"
    store = ConversationStore(str(path))

    newer = Conversation(id="newer", title="Newer", updated_at=datetime.now())
    older = Conversation(
        id="older",
        title="Older",
        updated_at=datetime.now() - timedelta(days=1),
    )

    # Use upsert instead of bulk_load
    store.upsert(older)
    store.upsert(newer)

    conversations = store.list_conversations()
    assert len(conversations) == 2
    # Verify both conversations are present
    ids = {c.id for c in conversations}
    assert "newer" in ids
    assert "older" in ids


def test_store_delete_conversation(tmp_path):
    """Test deleting a conversation from the store."""
    path = tmp_path / "conversations.json"
    store = ConversationStore(str(path))

    convo = Conversation(id="to_delete", title="Delete Me")
    store.upsert(convo)

    assert store.get("to_delete") is not None
    store.delete("to_delete")
    assert store.get("to_delete") is None
