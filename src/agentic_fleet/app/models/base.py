"""Base models and enums for the AgenticFleet API.

Contains common enumerations used across the API.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


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
    AGENT_OUTPUT = "agent.output"
    AGENT_COMPLETE = "agent.complete"

    # Connection/control events
    CONNECTED = "connected"
    CANCELLED = "cancelled"
    HEARTBEAT = "heartbeat"

    # Control events
    ERROR = "error"
    DONE = "done"


class MessageRole(StrEnum):
    """Role of a chat message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class EventCategory(StrEnum):
    """Semantic category for UI component routing.

    Maps workflow events to appropriate frontend components:
    - STEP -> WorkflowEvents/StepsItem (agent lifecycle)
    - THOUGHT -> ChainOfThought/ChatStep (internal reasoning)
    - REASONING -> Reasoning component (GPT-5 chain-of-thought)
    - PLANNING -> ChatStep with routing icon (routing decisions)
    - OUTPUT -> MessageBubble (agent outputs)
    - RESPONSE -> MessageBubble (final user-facing response)
    - STATUS -> WorkflowEvents status line
    - ERROR -> Error toast/step
    """

    STEP = "step"
    THOUGHT = "thought"
    REASONING = "reasoning"
    PLANNING = "planning"
    OUTPUT = "output"
    RESPONSE = "response"
    STATUS = "status"
    ERROR = "error"


class UIHint(BaseModel):
    """Hints for frontend UI component selection and rendering.

    Attributes:
        component: Suggested React component name.
        priority: Display priority (high items shown prominently).
        collapsible: Whether the item should be collapsible by default.
        icon_hint: Icon hint for the component (routing, analysis, quality, progress).
    """

    component: str = Field(..., description="Suggested UI component name")
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Display priority"
    )
    collapsible: bool = Field(default=True, description="Whether to show collapsed by default")
    icon_hint: str | None = Field(
        default=None, description="Icon hint (routing, analysis, quality, progress)"
    )
