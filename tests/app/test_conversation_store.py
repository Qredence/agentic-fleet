from datetime import datetime, timedelta

from agentic_fleet.core.conversation_store import ConversationStore
from agentic_fleet.models import Conversation, Message, MessageRole


def test_conversation_store_persists(tmp_path):
    path = tmp_path / "conversations.json"
    store = ConversationStore(path)

    convo = Conversation(id="c1", title="Test Chat")
    msg = Message(role=MessageRole.USER, content="hello", author="User")
    convo.messages.append(msg)
    store.upsert(convo)

    reloaded = ConversationStore(path).get("c1")

    assert reloaded is not None
    assert reloaded.title == "Test Chat"
    assert len(reloaded.messages) == 1
    assert reloaded.messages[0].author == "User"


def test_store_sorting_by_updated(tmp_path):
    path = tmp_path / "conversations.json"
    store = ConversationStore(path)

    newer = Conversation(id="newer", title="Newer", updated_at=datetime.now())
    older = Conversation(
        id="older",
        title="Older",
        updated_at=datetime.now() - timedelta(days=1),
    )

    store.bulk_load([older, newer])

    conversations = store.list_conversations()
    assert conversations[0].id == "newer"
