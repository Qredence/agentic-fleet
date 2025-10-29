"""Pydantic models for chat API endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of the message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ExecutionStatus(str, Enum):
    """Status of workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ChatMessage(BaseModel):
    """Single chat message."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: MessageRole
    content: str
    agent_id: str | None = None
    agent_type: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Request to create a new chat execution."""

    message: str = Field(..., min_length=1, description="User's chat message")
    workflow_id: str = Field(
        default="magentic_fleet",
        description="Workflow to execute (magentic_fleet or collaboration)",
    )
    conversation_id: str | None = Field(
        default=None, description="Optional conversation ID for context"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the execution"
    )


class ChatResponse(BaseModel):
    """Response from chat execution creation."""

    execution_id: str = Field(..., description="Unique execution ID")
    status: ExecutionStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    websocket_url: str | None = Field(
        default=None, description="WebSocket URL for streaming updates"
    )
    message: str = Field(default="Execution created", description="Status message")


class ExecutionStatusResponse(BaseModel):
    """Status of a workflow execution."""

    execution_id: str
    status: ExecutionStatus
    workflow_id: str
    started_at: datetime
    completed_at: datetime | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebSocketMessage(BaseModel):
    """Message sent over WebSocket connection."""

    type: str = Field(..., description="Message type (delta, message, complete, error)")
    execution_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionState(BaseModel):
    """Persisted state for workflow execution."""

    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    user_message: str
    conversation_id: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_status_response(self) -> ExecutionStatusResponse:
        """Convert to status response."""
        return ExecutionStatusResponse(
            execution_id=self.execution_id,
            status=self.status,
            workflow_id=self.workflow_id,
            started_at=self.started_at,
            completed_at=self.completed_at,
            messages=self.messages,
            error=self.error,
            metadata=self.metadata,
        )
