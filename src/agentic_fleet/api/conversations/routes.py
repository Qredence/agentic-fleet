from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agentic_fleet.api.conversations.service import (
    Conversation,
    ConversationMessage,
    ConversationNotFoundError,
    get_store,
)

router = APIRouter()


def _serialize_message(message: ConversationMessage) -> dict[str, str | int]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }


def _serialize_conversation(conversation: Conversation) -> dict[str, object]:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "messages": [_serialize_message(msg) for msg in conversation.messages],
    }


def create_conversation() -> dict[str, object]:
    store = get_store()
    conversation = store.create()
    return _serialize_conversation(conversation)


def list_conversations() -> dict[str, list[dict[str, object]]]:
    store = get_store()
    items = [_serialize_conversation(conv) for conv in store.list()]
    return {"items": items}


def get_conversation(conversation_id: str) -> dict[str, object]:
    store = get_store()
    try:
        conversation = store.get(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    return _serialize_conversation(conversation)


router.post("/conversations", status_code=201)(create_conversation)
router.get("/conversations")(list_conversations)
router.get("/conversations/{conversation_id}")(get_conversation)
