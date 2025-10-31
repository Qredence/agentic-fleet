from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

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


async def chat_stream(req: ChatRequest) -> EventSourceResponse:
    """Stream chat responses using Server-Sent Events.

    This endpoint provides real-time workflow execution updates as SSE events.
    Event types:
    - message.delta: Incremental content updates
    - message.done: Workflow completion signal
    """
    store = get_store()
    workflow_service = get_workflow_service()

    try:
        store.get(req.conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    store.add_message(req.conversation_id, role="user", content=req.message)

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        """Generate SSE events from workflow execution."""
        workflow = workflow_service._create_workflow()
        assistant_parts: list[str] = []

        try:
            events = workflow.run(req.message)
            async for event in events:
                event_type = event.get("type")

                if event_type == "message.delta":
                    data = event.get("data", {})
                    delta = data.get("delta", "") if isinstance(data, dict) else ""
                    if delta:
                        assistant_parts.append(str(delta))
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "delta", "delta": str(delta)}),
                    }
                elif event_type == "message.done":
                    yield {"event": "message", "data": json.dumps({"type": "done"})}
                    break

            # Store the complete assistant message
            assistant_message = "".join(assistant_parts)
            if assistant_message:
                store.add_message(req.conversation_id, role="assistant", content=assistant_message)

        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(event_generator())


router.post("/chat", response_model=ChatResponse)(chat)
router.post("/chat/stream")(chat_stream)
