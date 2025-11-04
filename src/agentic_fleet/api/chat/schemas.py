"""Schemas for chat API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request payload for chat endpoint.
    
    Attributes:
        conversation_id: Unique identifier for the conversation
        message: User's message content to process
    """
    conversation_id: str = Field(..., description="Conversation identifier")
    message: str = Field(..., description="User message content")


class ChatMessagePayload(BaseModel):
    """Represents a single chat message in a conversation.
    
    Attributes:
        id: Unique message identifier
        role: Message sender role (user, assistant, or system)
        content: Message text content
        created_at: Unix timestamp when message was created
    """
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: int


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    messages: list[ChatMessagePayload]
