"""Chat API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer


class Message(BaseModel):
    """Message schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str | int | None = None
    content: str
    role: str
    reasoning: str | None = None
    created_at: datetime | float | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime | float | None, _info: Any) -> float:
        """Serialize created_at to timestamp."""
        if isinstance(dt, datetime):
            return dt.timestamp()
        if isinstance(dt, float):
            return dt
        return 0.0


class Conversation(BaseModel):
    """Conversation schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str | int | None = None
    title: str | None = None
    created_at: datetime | float | None = None
    messages: list[Message] = []

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime | float | None, _info: Any) -> float:
        """Serialize created_at to timestamp."""
        if isinstance(dt, datetime):
            return dt.timestamp()
        if isinstance(dt, float):
            return dt
        return 0.0


class CreateConversationRequest(BaseModel):
    """Create conversation request schema."""

    title: str | None = "New Conversation"


class ChatRequest(BaseModel):
    """Chat request schema."""

    conversation_id: str | int
    message: str
    stream: bool = True


class ChatResponse(BaseModel):
    """Chat response schema."""

    conversation_id: str | int
    message: str
    messages: list[Message]


class ConversationListResponse(BaseModel):
    """Conversation list response schema."""

    items: list[Conversation]
