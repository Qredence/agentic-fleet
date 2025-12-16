"""Conversation routes.

Provides CRUD operations for chat conversations.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from agentic_fleet.api.deps import ConversationManagerDep
from agentic_fleet.models import Conversation, CreateConversationRequest

router = APIRouter()


@router.post(
    "/conversations",
    response_model=Conversation,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_conversation(
    request: CreateConversationRequest,
    manager: ConversationManagerDep,
) -> Conversation:
    """Create a new chat conversation."""
    return manager.create_conversation(title=request.title)


@router.get(
    "/conversations",
    response_model=list[Conversation],
    summary="List all conversations",
)
async def list_conversations(manager: ConversationManagerDep) -> list[Conversation]:
    """List all available conversations."""
    return manager.list_conversations()


@router.get(
    "/conversations/{conversation_id}",
    response_model=Conversation,
    summary="Get conversation details",
)
async def get_conversation(
    conversation_id: str,
    manager: ConversationManagerDep,
) -> Conversation:
    """Get a conversation by ID."""
    conversation = manager.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return conversation
