"""Request models for the AgenticFleet API.

Defines request schemas for various API endpoints.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    title: str = "New Chat"


class RunRequest(BaseModel):
    """Request model for workflow execution.

    Attributes:
        task: The task description to execute.
        mode: Execution mode (standard, parallel, sequential, etc.).
        additional_context: Optional context to pass to the workflow.
    """

    task: str = Field(..., min_length=1, description="The task to execute")
    mode: str = Field(default="standard", description="Execution mode")
    additional_context: dict[str, Any] | None = Field(
        default=None, description="Additional context for the workflow"
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "task": "Analyze the latest market trends for AI startups",
                    "mode": "standard",
                    "additional_context": {"focus": "Series A funding"},
                }
            ]
        },
    )


class ChatRequest(BaseModel):
    """Request model for streaming chat endpoint.

    Attributes:
        message: The user message/task to execute.
        conversation_id: Optional conversation ID for context continuity.
        stream: Whether to stream the response (default True).
        reasoning_effort: Per-request reasoning effort override for GPT-5 models.
        enable_checkpointing: Whether to persist checkpoints during a new run.
        checkpoint_id: Optional checkpoint identifier for pause/resume support.
    """

    message: str = Field(..., min_length=1, description="User message or task")
    conversation_id: str | None = Field(default=None, description="Conversation ID")
    stream: bool = Field(default=True, description="Enable streaming")
    reasoning_effort: Literal["minimal", "medium", "maximal"] | None = Field(
        default=None, description="Reasoning effort for GPT-5 models (overrides config)"
    )
    enable_checkpointing: bool = Field(
        default=False,
        description=(
            "Enable checkpoint persistence for this new run. "
            "This is distinct from resume: to resume, use the `workflow.resume` WebSocket message."
        ),
    )
    checkpoint_id: str | None = Field(
        default=None,
        description=(
            "Optional checkpoint identifier for resuming a previously checkpointed workflow. "
            "In agent-framework, `message` and `checkpoint_id` are mutually exclusive. "
            "For the WebSocket chat endpoint, sending `checkpoint_id` alongside `message` is deprecated; "
            "use `enable_checkpointing` for new runs or `workflow.resume` to resume."
        ),
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "message": "Analyze the latest AI trends",
                    "stream": True,
                    "reasoning_effort": "medium",
                    "enable_checkpointing": True,
                }
            ]
        },
    )


class WorkflowResumeRequest(BaseModel):
    """WebSocket message to resume a previously checkpointed workflow.

    This message is only valid for the `/api/ws/chat` endpoint and is intentionally
    separate from ChatRequest to match agent-framework's contract: a resume call must
    omit the message/task and provide only `checkpoint_id`.
    """

    type: Literal["workflow.resume"] = Field(
        default="workflow.resume",
        description="Discriminator for resume requests over WebSocket",
    )
    conversation_id: str | None = Field(default=None, description="Conversation ID")
    checkpoint_id: str = Field(..., min_length=1, description="Checkpoint identifier to resume")
    stream: bool = Field(default=True, description="Enable streaming")
    reasoning_effort: Literal["minimal", "medium", "maximal"] | None = Field(
        default=None, description="Reasoning effort for GPT-5 models (overrides config)"
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "type": "workflow.resume",
                    "conversation_id": "conv-123",
                    "checkpoint_id": "ckpt-abc",
                    "stream": True,
                }
            ]
        },
    )
