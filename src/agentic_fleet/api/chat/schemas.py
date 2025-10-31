"""Schemas for chat API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation identifier")
    message: str = Field(..., description="User message content")


class ChatMessagePayload(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: int


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    messages: list[ChatMessagePayload]
