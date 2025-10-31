from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agentic_fleet.api.chat.schemas import ChatMessagePayload, ChatRequest, ChatResponse
from agentic_fleet.api.chat.service import get_workflow_service
from agentic_fleet.api.conversations.service import ConversationNotFoundError, get_store

router = APIRouter()


async def chat(req: ChatRequest) -> ChatResponse:
    store = get_store()
    workflow_service = get_workflow_service()

    try:
        store.get(req.conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    store.add_message(req.conversation_id, role="user", content=req.message)

    assistant_message = await workflow_service.execute_workflow(req.message)
    store.add_message(req.conversation_id, role="assistant", content=assistant_message)

    conversation = store.get(req.conversation_id)

    response_messages = [
        ChatMessagePayload(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )
        for message in conversation.messages
    ]

    return ChatResponse(
        conversation_id=conversation.id,
        message=assistant_message,
        messages=response_messages,
    )


router.post("/chat", response_model=ChatResponse)(chat)
