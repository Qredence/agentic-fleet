from __future__ import annotations

from fastapi import APIRouter

from agentic_fleet.api.conversations.persistence_adapter import get_persistence_adapter
from agentic_fleet.api.conversations.schemas import (
    ConversationResponse,
    ConversationsListResponse,
    MessageResponse,
)
from agentic_fleet.api.conversations.service import ConversationNotFoundError
from agentic_fleet.api.exceptions import ConversationMissingError

router: APIRouter = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation() -> ConversationResponse:
    persistence_adapter = get_persistence_adapter()
    conversation = await persistence_adapter.create()
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                reasoning=msg.reasoning,
            )
            for msg in conversation.messages
        ],
    )


@router.get("/conversations", response_model=ConversationsListResponse)
async def list_conversations() -> ConversationsListResponse:
    persistence_adapter = get_persistence_adapter()
    items: list[ConversationResponse] = []
    for conv in await persistence_adapter.list():
        items.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                messages=[
                    MessageResponse(
                        id=msg.id,
                        role=msg.role,
                        content=msg.content,
                        created_at=msg.created_at,
                        reasoning=msg.reasoning,
                    )
                    for msg in conv.messages
                ],
            )
        )
    return ConversationsListResponse(items=items)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str) -> ConversationResponse:
    persistence_adapter = get_persistence_adapter()
    try:
        conversation = await persistence_adapter.get(conversation_id)
    except ConversationNotFoundError as exc:
        raise ConversationMissingError(conversation_id) from exc
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                reasoning=msg.reasoning,
            )
            for msg in conversation.messages
        ],
    )
