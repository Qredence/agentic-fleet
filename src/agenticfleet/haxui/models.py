from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field


class EntityInfo(BaseModel):
    """Metadata returned to the frontend for an agent or workflow."""

    id: str
    type: Literal["agent", "workflow"]
    name: str
    framework: str = "agenticfleet"
    description: str | None = None
    tools: list[Any] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: Literal["directory", "in_memory", "remote_gallery"] = "directory"
    instructions: str | None = None
    model: str | None = None
    chat_client_type: str | None = None
    context_providers: list[str] | None = None
    middleware: list[str] | None = None
    # Workflow specific fields
    executors: list[str] | None = None
    workflow_dump: dict[str, Any] | None = None
    input_schema: dict[str, Any] | None = None
    input_type_name: str | None = None
    start_executor_id: str | None = None


class DiscoveryResponse(BaseModel):
    """Container for entity discovery results."""

    entities: list[EntityInfo]


class ConversationSummary(BaseModel):
    """Summary metadata about a conversation."""

    id: str
    object: Literal["conversation"] = "conversation"
    created_at: int = Field(default_factory=lambda: int(time.time()))
    metadata: dict[str, str] | None = None


class ConversationListResponse(BaseModel):
    """List response mirroring OpenAI conversation API."""

    object: Literal["list"] = "list"
    data: list[ConversationSummary]
    has_more: bool = False


class ConversationItem(BaseModel):
    """Message stored per conversation."""

    id: str
    type: Literal["message"]
    role: Literal["user", "assistant", "system", "tool"]
    content: list[dict[str, Any]]
    status: Literal["in_progress", "completed", "incomplete"] = "completed"
    created_at: int = Field(default_factory=lambda: int(time.time()))


class ConversationItemsResponse(BaseModel):
    """Response payload for conversation items."""

    data: list[ConversationItem]
    has_more: bool = False


class HealthResponse(BaseModel):
    """Simple health check payload."""

    status: Literal["healthy"] = "healthy"
    version: str
    agents_dir: str | None = None


class ApprovalRequestInfo(BaseModel):
    """Details about a pending approval request."""

    request_id: str
    operation_type: str
    agent_name: str
    operation: str
    details: dict[str, Any] = Field(default_factory=dict)
    code: str | None = None
    status: str = "pending"
    timestamp: str


class ApprovalListResponse(BaseModel):
    """List of pending approval requests."""

    data: list[ApprovalRequestInfo]


class ApprovalDecisionRequest(BaseModel):
    """Payload submitted to approve or reject a request."""

    decision: Literal["approved", "rejected", "modified"]
    reason: str | None = None
    modified_code: str | None = None
