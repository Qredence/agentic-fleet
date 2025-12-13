"""Conversation models for the AgenticFleet API.

Defines conversation and message schemas.
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .base import MessageRole


class Message(BaseModel):
    """A single chat message.

    Attributes:
        role: The sender's role.
        content: The message content.
        created_at: Creation timestamp.
        author: Optional human-readable author or agent name.
        agent_id: Agent identifier if applicable.
        id: Unique message ID.
    """

    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    author: str | None = Field(default=None, description="Author or agent display name")
    agent_id: str | None = Field(default=None, description="Agent identifier if applicable")
    workflow_id: str | None = Field(
        default=None,
        description="Optional workflow identifier associated with this message (e.g. streaming session id)",
    )
    quality_score: float | None = Field(
        default=None,
        description="Optional quality score for the assistant message (0-10 scale)",
        ge=0,
        le=10,
    )
    quality_flag: str | None = Field(
        default=None,
        description="Optional quality flag for the assistant message",
    )
    quality_pending: bool = Field(
        default=False,
        description="True if quality evaluation is pending for this message",
    )
    quality_details: dict[str, object] | None = Field(
        default=None,
        description="Optional structured quality details/metrics",
    )
    id: str = Field(default_factory=lambda: uuid4().hex)

    model_config = ConfigDict(from_attributes=True)


class Conversation(BaseModel):
    """A chat conversation history.

    Attributes:
        id: Unique conversation ID.
        title: Conversation title.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        messages: List of messages in the conversation.
    """

    id: str
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: list[Message] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
