"""Request models for the AgenticFleet API.

Defines request schemas for various API endpoints.
"""

from typing import Any

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
    """

    message: str = Field(..., min_length=1, description="User message or task")
    conversation_id: str | None = Field(default=None, description="Conversation ID")
    stream: bool = Field(default=True, description="Enable streaming")
    reasoning_effort: str | None = Field(
        default=None, description="Reasoning effort for GPT-5 models (overrides config)"
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "message": "Analyze the latest AI trends",
                    "stream": True,
                    "reasoning_effort": "medium",
                }
            ]
        },
    )
