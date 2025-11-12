"""Request and response models for workflow execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkflowRunRequest(BaseModel):
    """Structured request payload for executing a workflow run."""

    message: str = Field(description="User input or task prompt")
    conversation_id: str | None = Field(default=None, description="Conversation identifier")
    correlation_id: str | None = Field(default=None, description="Tracing correlation ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata forwarded to the workflow context",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context values made available to workflow participants",
    )
    agents: list[str] | None = Field(
        default=None,
        description="Optional subset of agent IDs to instantiate for this request",
    )
    use_cache: bool = Field(
        default=True,
        description="Whether workflow execution is eligible for cache reuse",
    )


class WorkflowResumeRequest(BaseModel):
    """Structured request payload for resuming a workflow from a checkpoint."""

    checkpoint_id: str = Field(description="Checkpoint identifier to resume from")
    conversation_id: str | None = Field(default=None, description="Conversation identifier")
    correlation_id: str | None = Field(default=None, description="Tracing correlation ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata forwarded to the workflow context",
    )
    use_cache: bool = Field(
        default=False,
        description="Whether resume execution should leverage cached responses",
    )


class WorkflowRunResponse(BaseModel):
    """Metadata returned when executing a workflow run."""

    workflow_id: str = Field(description="Workflow identifier")
    conversation_id: str | None = Field(default=None, description="Conversation identifier")
    correlation_id: str | None = Field(default=None, description="Tracing correlation ID")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Run start timestamp")
    cached: bool = Field(default=False, description="Whether the response was served from cache")


class WorkflowCheckpointMetadata(BaseModel):
    """Metadata about a persisted workflow checkpoint."""

    checkpoint_id: str = Field(description="Unique checkpoint identifier")
    workflow_id: str = Field(description="Workflow identifier")
    conversation_id: str | None = Field(default=None, description="Conversation identifier")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Checkpoint creation time"
    )
    path: str = Field(description="Filesystem path where checkpoint is stored")


__all__ = [
    "WorkflowCheckpointMetadata",
    "WorkflowResumeRequest",
    "WorkflowRunRequest",
    "WorkflowRunResponse",
]
