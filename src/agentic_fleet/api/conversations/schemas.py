"""Pydantic response models for conversation endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    id: str = Field(description="Unique message identifier")
    role: Literal["user", "assistant", "system"] = Field(description="Message role")
    content: str = Field(description="Message content")
    created_at: int = Field(description="Unix timestamp of creation")
    reasoning: str | None = Field(default=None, description="Optional reasoning trace")


class ConversationResponse(BaseModel):
    id: str = Field(description="Conversation identifier")
    title: str = Field(description="Conversation title")
    created_at: int = Field(description="Creation timestamp")
    messages: list[MessageResponse] = Field(description="Ordered list of messages")

    model_config = ConfigDict(extra="allow")


class ConversationsListResponse(BaseModel):
    items: list[ConversationResponse] = Field(description="List of conversations")

    model_config = ConfigDict(extra="allow")


__all__ = [
    "ConversationResponse",
    "ConversationsListResponse",
    "MessageResponse",
]
