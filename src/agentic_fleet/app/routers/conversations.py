"""Conversations router.

Provides endpoints for creating, retrieving, and managing chat conversations.
"""

from fastapi import APIRouter, HTTPException, status

from agentic_fleet.app.dependencies import ConversationManagerDep
from agentic_fleet.app.schemas import Conversation, CreateConversationRequest

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
    """Create a new chat conversation.

    Args:
        request: The creation request.
        manager: The conversation manager.

    Returns:
        The created Conversation.
    """
    return manager.create_conversation(title=request.title)


@router.get(
    "/conversations",
    response_model=list[Conversation],
    summary="List all conversations",
)
async def list_conversations(
    manager: ConversationManagerDep,
) -> list[Conversation]:
    """List all available conversations.

    Args:
        manager: The conversation manager.

    Returns:
        List of conversations sorted by last update.
    """
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
    """Retrieve details for a specific conversation.

    Args:
        conversation_id: The conversation ID.
        manager: The conversation manager.

    Returns:
        The conversation with messages.

    Raises:
        HTTPException: If conversation not found.
    """
    conversation = manager.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    return conversation
