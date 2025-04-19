"""
Pydantic schemas for message-related data.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Enum for message types."""

    TEXT = "text"
    IMAGE = "image"
    CODE = "code"
    FILE = "file"
    SYSTEM = "system"


class MessageBase(BaseModel):
    """Base schema for message data."""

    content: str = Field(..., description="Content of the message")
    sender: str = Field(..., description="ID or name of the sender")
    receiver: str = Field(..., description="ID or name of the receiver")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""

    session_id: str = Field(..., description="ID of the chat session")
    parent_id: Optional[str] = Field(None, description="ID of the parent message (for threading)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional message metadata")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Attached files or media")


class MessageUpdate(BaseModel):
    """Schema for updating an existing message."""

    content: Optional[str] = Field(None, description="Content of the message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")
    is_edited: Optional[bool] = Field(None, description="Whether the message has been edited")


class Message(MessageBase):
    """Complete message schema with all fields."""

    id: str = Field(..., description="Unique identifier for the message")
    session_id: str = Field(..., description="ID of the chat session")
    parent_id: Optional[str] = Field(None, description="ID of the parent message (for threading)")
    timestamp: datetime = Field(..., description="When the message was sent")
    edited_at: Optional[datetime] = Field(None, description="When the message was last edited")
    is_edited: bool = Field(default=False, description="Whether the message has been edited")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional message metadata")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Attached files or media")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
