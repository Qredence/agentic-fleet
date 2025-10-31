from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException

from agentic_fleet.api.chat.schemas import ChatMessagePayload, ChatRequest, ChatResponse
from agentic_fleet.api.conversations.service import ConversationNotFoundError, get_store
from agentic_fleet.api.workflows.service import WorkflowEvent, create_magentic_fleet_workflow

router = APIRouter()


async def _run_workflow(message: str) -> str:
    workflow = create_magentic_fleet_workflow()
    parts: list[str] = []
    events: AsyncGenerator[WorkflowEvent, None] = workflow.run(message)
    async for event in events:
        event_type = event.get("type")
        if event_type == "message.delta":
            data = event.get("data", {})
            delta = data.get("delta", "") if isinstance(data, dict) else ""
            parts.append(str(delta))
        elif event_type == "message.done":
            break
    return "".join(parts)


async def chat(req: ChatRequest) -> ChatResponse:
    store = get_store()
    try:
        store.get(req.conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    store.add_message(req.conversation_id, role="user", content=req.message)

    assistant_message = await _run_workflow(req.message)
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
