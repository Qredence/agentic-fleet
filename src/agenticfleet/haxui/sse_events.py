"""
Structured SSE event models for frontend-backend communication.
These Pydantic models ensure type safety and consistent event structure.
"""

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """SSE event type discriminator"""

    AGENT_RESPONSE = "agent_response"
    TOOL_CALL = "tool_call"
    APPROVAL_REQUEST = "approval_request"
    PROGRESS = "progress"
    ERROR = "error"
    COMPLETE = "complete"


class RiskLevel(str, Enum):
    """Risk classification for approval requests"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SSEEvent(BaseModel):
    """Base SSE event structure"""

    type: EventType
    timestamp: float = Field(default_factory=time.time)

    def to_sse(self) -> bytes:
        """Convert to SSE format"""
        return f"data: {self.model_dump_json()}\n\n".encode()


class AgentResponseEvent(SSEEvent):
    """Agent text response chunk"""

    type: EventType = EventType.AGENT_RESPONSE
    agent: str
    content: str
    isComplete: bool = False


class ToolCallEvent(SSEEvent):
    """Tool execution notification"""

    type: EventType = EventType.TOOL_CALL
    tool: str
    args: dict[str, Any]
    result: Any | None = None


class ApprovalRequestEvent(SSEEvent):
    """Human-in-the-loop approval request"""

    type: EventType = EventType.APPROVAL_REQUEST
    id: str
    operation: str
    params: dict[str, Any]
    context: str
    risk_level: RiskLevel | None = None


class ProgressEvent(SSEEvent):
    """Workflow progress update"""

    type: EventType = EventType.PROGRESS
    step: str
    progress: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    message: str


class ErrorEvent(SSEEvent):
    """Error notification"""

    type: EventType = EventType.ERROR
    error: str
    details: str | None = None
    recoverable: bool = True


class CompleteEvent(SSEEvent):
    """Workflow completion"""

    type: EventType = EventType.COMPLETE
    result: Any
    summary: str | None = None


class SSEEventEmitter:
    """Helper class to emit properly formatted SSE events"""

    @staticmethod
    def emit_agent_response(agent: str, content: str, is_complete: bool = False) -> bytes:
        """Emit agent response chunk"""
        event = AgentResponseEvent(agent=agent, content=content, isComplete=is_complete)
        return event.to_sse()

    @staticmethod
    def emit_tool_call(tool: str, args: dict[str, Any], result: Any = None) -> bytes:
        """Emit tool call notification"""
        event = ToolCallEvent(tool=tool, args=args, result=result)
        return event.to_sse()

    @staticmethod
    def emit_approval_request(
        id: str,
        operation: str,
        params: dict[str, Any],
        context: str,
        risk_level: RiskLevel | None = None,
    ) -> bytes:
        """Emit approval request"""
        event = ApprovalRequestEvent(
            id=id,
            operation=operation,
            params=params,
            context=context,
            risk_level=risk_level,
        )
        return event.to_sse()

    @staticmethod
    def emit_progress(step: str, progress: float, message: str) -> bytes:
        """Emit progress update"""
        # Clamp progress to 0.0-1.0
        progress = min(1.0, max(0.0, progress))
        event = ProgressEvent(step=step, progress=progress, message=message)
        return event.to_sse()

    @staticmethod
    def emit_error(error: str, details: str | None = None, recoverable: bool = True) -> bytes:
        """Emit error event"""
        event = ErrorEvent(error=error, details=details, recoverable=recoverable)
        return event.to_sse()

    @staticmethod
    def emit_complete(result: Any, summary: str | None = None) -> bytes:
        """Emit completion event"""
        event = CompleteEvent(result=result, summary=summary)
        return event.to_sse()
