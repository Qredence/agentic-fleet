"""Pydantic models for Server-Sent Events (SSE) streaming."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    """Types of SSE events that can be emitted."""

    # Workflow lifecycle events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_ERROR = "workflow.error"

    # Agent events
    AGENT_MESSAGE = "agent.message"
    AGENT_DELTA = "agent.delta"
    AGENT_THINKING = "agent.thinking"

    # Manager/orchestrator events
    ORCHESTRATOR_MESSAGE = "orchestrator.message"
    ORCHESTRATOR_PLANNING = "orchestrator.planning"
    ORCHESTRATOR_DECISION = "orchestrator.decision"

    # Tool execution events
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"

    # Approval events
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RESPONDED = "approval.responded"

    # Final result
    FINAL_RESULT = "final.result"

    # System events
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class SSEEvent(BaseModel):
    """Base model for Server-Sent Events."""

    event: SSEEventType = Field(
        description="Type of SSE event",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload data",
    )
    id: str | None = Field(
        default=None,
        description="Optional event ID for tracking",
    )
    retry: int | None = Field(
        default=None,
        description="Optional retry interval in milliseconds",
    )

    def to_sse_format(self) -> str:
        """Convert to SSE wire format.

        SSE format:
            event: event_type
            data: {"key": "value"}
            id: optional_id
            retry: optional_retry_ms

        """
        lines = []

        # Event type
        lines.append(f"event: {self.event.value}")

        # Data (JSON serialized)
        import json

        lines.append(f"data: {json.dumps(self.data)}")

        # Optional fields
        if self.id is not None:
            lines.append(f"id: {self.id}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        # SSE messages end with double newline
        lines.append("")
        lines.append("")

        return "\n".join(lines)

    @classmethod
    def workflow_started(
        cls,
        workflow_id: str,
        workflow_name: str,
        **kwargs: Any,
    ) -> SSEEvent:
        """Create a workflow started event."""
        return cls(
            event=SSEEventType.WORKFLOW_STARTED,
            data={
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                **kwargs,
            },
        )

    @classmethod
    def workflow_completed(
        cls,
        workflow_id: str,
        result: Any,
        **kwargs: Any,
    ) -> SSEEvent:
        """Create a workflow completed event."""
        return cls(
            event=SSEEventType.WORKFLOW_COMPLETED,
            data={
                "workflow_id": workflow_id,
                "result": result,
                **kwargs,
            },
        )

    @classmethod
    def agent_delta(
        cls,
        agent_id: str,
        text: str,
        **kwargs: Any,
    ) -> SSEEvent:
        """Create an agent delta event (streaming output)."""
        return cls(
            event=SSEEventType.AGENT_DELTA,
            data={
                "agent_id": agent_id,
                "text": text,
                **kwargs,
            },
        )

    @classmethod
    def agent_message(
        cls,
        agent_id: str,
        message: str,
        **kwargs: Any,
    ) -> SSEEvent:
        """Create an agent message event (complete output)."""
        return cls(
            event=SSEEventType.AGENT_MESSAGE,
            data={
                "agent_id": agent_id,
                "message": message,
                **kwargs,
            },
        )

    @classmethod
    def orchestrator_message(
        cls,
        kind: str,
        message: str,
        **kwargs: Any,
    ) -> SSEEvent:
        """Create an orchestrator message event."""
        return cls(
            event=SSEEventType.ORCHESTRATOR_MESSAGE,
            data={
                "kind": kind,
                "message": message,
                **kwargs,
            },
        )

    @classmethod
    def final_result(
        cls,
        result: Any,
        **kwargs: Any,
    ) -> SSEEvent:
        """Create a final result event."""
        return cls(
            event=SSEEventType.FINAL_RESULT,
            data={
                "result": result,
                **kwargs,
            },
        )

    @classmethod
    def error(
        cls,
        error: str,
        **kwargs: Any,
    ) -> SSEEvent:
        """Create an error event."""
        return cls(
            event=SSEEventType.ERROR,
            data={
                "error": error,
                **kwargs,
            },
        )

    @classmethod
    def heartbeat(cls) -> SSEEvent:
        """Create a heartbeat event."""
        return cls(
            event=SSEEventType.HEARTBEAT,
            data={"timestamp": None},  # Will be filled by server
        )
