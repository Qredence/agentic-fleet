from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agentic_fleet.api.conversations.persistence_adapter import get_persistence_adapter
from agentic_fleet.api.conversations.service import (
    Conversation,
    ConversationMessage,
    ConversationNotFoundError,
)

router = APIRouter()


def _serialize_message(message: ConversationMessage) -> dict[str, str | int | None]:
    result: dict[str, str | int | None] = {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }
    if message.reasoning is not None:
        result["reasoning"] = message.reasoning
    return result


def _serialize_conversation(conversation: Conversation) -> dict[str, object]:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "messages": [_serialize_message(msg) for msg in conversation.messages],
    }


async def create_conversation() -> dict[str, object]:
    persistence_adapter = get_persistence_adapter()
    conversation = await persistence_adapter.create()
    return _serialize_conversation(conversation)


async def list_conversations() -> dict[str, list[dict[str, object]]]:
    persistence_adapter = get_persistence_adapter()
    items = [_serialize_conversation(conv) for conv in await persistence_adapter.list()]
    return {"items": items}


async def get_conversation(conversation_id: str) -> dict[str, object]:
    persistence_adapter = get_persistence_adapter()
    try:
        conversation = await persistence_adapter.get(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    return _serialize_conversation(conversation)


router.post("/conversations", status_code=201)(create_conversation)
router.get("/conversations")(list_conversations)
router.get("/conversations/{conversation_id}")(get_conversation)
