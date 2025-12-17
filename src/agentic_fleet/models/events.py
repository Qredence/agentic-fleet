"""SSE event models for the AgenticFleet API.

Defines streaming event schemas for Server-Sent Events.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .base import EventCategory, StreamEventType, UIHint


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
    author: str | None = Field(default=None, description="Human-readable agent/author name")
    role: str | None = Field(
        default=None, description="Role of chat message if applicable (user/assistant/system)"
    )
    kind: str | None = Field(default=None, description="Event kind")
    error: str | None = Field(default=None, description="Error message")
    reasoning_partial: bool | None = Field(
        default=None, description="True if reasoning was interrupted"
    )
    data: dict[str, Any] | None = Field(default=None, description="Additional data")
    timestamp: datetime = Field(default_factory=datetime.now)
    category: EventCategory | None = Field(
        default=None, description="Semantic category for UI component routing"
    )
    ui_hint: UIHint | None = Field(
        default=None, description="Hints for frontend UI component selection"
    )
    workflow_id: str | None = Field(
        default=None, description="Workflow identifier for correlating streaming events"
    )
    log_line: str | None = Field(
        default=None,
        description="Human-friendly terminal log line mirrored to the frontend",
    )
    quality_score: float | None = Field(
        default=None,
        description="Heuristic or model-derived quality score for final answers (0..1)",
    )
    quality_flag: str | None = Field(
        default=None,
        description="Optional quality flag (e.g., low_confidence, empty)",
    )

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
        if self.author is not None:
            result["author"] = self.author
        if self.role is not None:
            result["role"] = self.role
        if self.kind is not None:
            result["kind"] = self.kind
        if self.error is not None:
            result["error"] = self.error
        if self.reasoning_partial is not None:
            result["reasoning_partial"] = self.reasoning_partial
        if self.data is not None:
            result["data"] = self.data
        if self.category is not None:
            result["category"] = self.category.value
        if self.ui_hint is not None:
            result["ui_hint"] = {
                "component": self.ui_hint.component,
                "priority": self.ui_hint.priority,
                "collapsible": self.ui_hint.collapsible,
            }
            if self.ui_hint.icon_hint is not None:
                result["ui_hint"]["icon_hint"] = self.ui_hint.icon_hint
        if self.workflow_id is not None:
            result["workflow_id"] = self.workflow_id
        if self.log_line is not None:
            result["log_line"] = self.log_line
        if self.quality_score is not None:
            result["quality_score"] = self.quality_score
        if self.quality_flag is not None:
            result["quality_flag"] = self.quality_flag

        result["timestamp"] = self.timestamp.isoformat()
        return result
