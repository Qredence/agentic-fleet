"""Pydantic schemas for the AgenticFleet API.

Defines request/response models for workflow execution,
agent information, streaming events, and related data structures.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Enums
# =============================================================================


class WorkflowStatus(StrEnum):
    """Status of a workflow session."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StreamEventType(StrEnum):
    """Types of events that can be streamed via SSE.

    Aligned with frontend StreamEventType in api/types.ts.
    """

    # Orchestrator events
    ORCHESTRATOR_MESSAGE = "orchestrator.message"
    ORCHESTRATOR_THOUGHT = "orchestrator.thought"

    # Response events
    RESPONSE_DELTA = "response.delta"
    RESPONSE_COMPLETED = "response.completed"

    # Reasoning events (GPT-5 verbose reasoning)
    REASONING_DELTA = "reasoning.delta"
    REASONING_COMPLETED = "reasoning.completed"

    # Agent events
    AGENT_START = "agent.start"
    AGENT_MESSAGE = "agent.message"
    AGENT_COMPLETE = "agent.complete"

    # Control events
    ERROR = "error"
    DONE = "done"


# =============================================================================
# Basic Request/Response Models
# =============================================================================


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


class RunResponse(BaseModel):
    """Response model for workflow execution results.

    Attributes:
        result: The execution result as a string.
        status: Execution status (completed, failed, etc.).
        execution_id: Unique identifier for this execution.
        metadata: Additional metadata about the execution.
    """

    result: str = Field(..., description="Execution result")
    status: str = Field(..., description="Execution status")
    execution_id: str = Field(..., description="Unique execution identifier")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Execution metadata")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "result": "Analysis complete. Key findings: ...",
                    "status": "completed",
                    "execution_id": "wf-abc123-def456",
                    "metadata": {
                        "duration_seconds": 12.5,
                        "agents_used": ["researcher", "analyst"],
                    },
                }
            ]
        },
    )


class AgentInfo(BaseModel):
    """Information about an available agent.

    Attributes:
        name: The agent's name.
        description: Human-readable description of the agent's capabilities.
        type: The agent type (DSPyEnhancedAgent, StandardAgent, etc.).
    """

    name: str = Field(..., description="Agent name")
    description: str = Field(default="", description="Agent description")
    type: str = Field(..., description="Agent type")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Streaming Request/Response Models
# =============================================================================


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
    reasoning_effort: Literal["minimal", "medium", "maximal"] | None = Field(
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


class WorkflowSession(BaseModel):
    """Workflow session metadata for tracking active workflows.

    Attributes:
        workflow_id: Unique identifier for the workflow.
        task: The task being executed.
        status: Current workflow status.
        created_at: When the workflow was created.
        started_at: When execution started.
        completed_at: When execution completed.
    """

    workflow_id: str = Field(..., description="Unique workflow identifier")
    task: str = Field(..., description="Task being executed")
    status: WorkflowStatus = Field(default=WorkflowStatus.CREATED)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    reasoning_effort: str | None = Field(default=None, description="Reasoning effort setting")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SSE Stream Event Models
# =============================================================================


class StreamEvent(BaseModel):
    """A streaming event sent via Server-Sent Events (SSE).

    Attributes:
        type: The event type (matches StreamEventType enum).
        message: Optional message content for orchestrator events.
        delta: Incremental text for response.delta events.
        reasoning: Incremental reasoning text for GPT-5 models.
        agent_id: Agent identifier for agent-specific events.
        kind: Event kind (thought, analysis, routing, quality).
        error: Error message for error events.
        reasoning_partial: True if reasoning was interrupted mid-stream.
        data: Arbitrary additional data.
        timestamp: Event timestamp.
    """

    type: StreamEventType = Field(..., description="Event type")
    message: str | None = Field(default=None, description="Message content")
    delta: str | None = Field(default=None, description="Incremental response text")
    reasoning: str | None = Field(default=None, description="Incremental reasoning text")
    agent_id: str | None = Field(default=None, description="Agent identifier")
    kind: str | None = Field(default=None, description="Event kind")
    error: str | None = Field(default=None, description="Error message")
    reasoning_partial: bool | None = Field(
        default=None, description="True if reasoning was interrupted"
    )
    data: dict[str, Any] | None = Field(default=None, description="Additional data")
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(extra="allow")

    def to_sse_dict(self) -> dict[str, Any]:
        """Convert to SSE-compatible dictionary with non-None fields only.

        Returns:
            Dictionary suitable for JSON serialization in SSE data field.
        """
        result: dict[str, Any] = {"type": self.type.value}

        if self.message is not None:
            result["message"] = self.message
        if self.delta is not None:
            result["delta"] = self.delta
        if self.reasoning is not None:
            result["reasoning"] = self.reasoning
        if self.agent_id is not None:
            result["agent_id"] = self.agent_id
        if self.kind is not None:
            result["kind"] = self.kind
        if self.error is not None:
            result["error"] = self.error
        if self.reasoning_partial is not None:
            result["reasoning_partial"] = self.reasoning_partial
        if self.data is not None:
            result["data"] = self.data

        result["timestamp"] = self.timestamp.isoformat()
        return result
