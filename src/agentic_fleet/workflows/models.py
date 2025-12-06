"""Workflow data models, messages, and streaming events.

Defines the data structures used to pass state between workflow executors,
including analysis results, routing plans, execution outcomes, quality reports,
typed message dataclasses, and streaming event helpers.

Consolidated from: models.py, messages.py, execution/streaming_events.py
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import WorkflowEvent

from agentic_fleet.utils.models import ExecutionMode, RoutingDecision

StreamPayload = Mapping[str, Any]


# =============================================================================
# Analysis/Routing/Execution Data Models
# =============================================================================


@dataclass(frozen=True)
class AnalysisResult:
    """Normalized task analysis returned by the analysis phase."""

    complexity: str
    capabilities: list[str] = field(default_factory=list)
    tool_requirements: list[str] = field(default_factory=list)
    steps: int = 3
    search_context: str = ""
    needs_web_search: bool = False
    search_query: str = ""


@dataclass(frozen=True)
class RoutingPlan:
    """Routing decision alongside supplemental orchestration metadata."""

    decision: RoutingDecision
    edge_cases: list[str] = field(default_factory=list)
    used_fallback: bool = False


@dataclass(frozen=True)
class ExecutionOutcome:
    """Result of executing the delegated/sequential/parallel phase."""

    result: str
    mode: ExecutionMode
    artifacts: dict[str, Any] = field(default_factory=dict)
    status: str = "success"
    assigned_agents: list[str] = field(default_factory=list)
    subtasks: list[str] = field(default_factory=list)
    tool_usage: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ProgressReport:
    """Structured progress evaluation data."""

    action: str
    feedback: str = ""
    used_fallback: bool = False


@dataclass(frozen=True)
class QualityReport:
    """Structured quality assessment including optional judge metadata."""

    score: float
    missing: str = ""
    improvements: str = ""
    judge_score: float | None = None
    final_evaluation: dict[str, Any] | None = None
    used_fallback: bool = False


# =============================================================================
# Typed Message Dataclasses (from messages.py)
# =============================================================================


@dataclass(frozen=True)
class TaskMessage:
    """Initial task message that starts the workflow."""

    task: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisMessage:
    """Message containing task analysis results."""

    task: str
    analysis: AnalysisResult
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingMessage:
    """Message containing routing decision."""

    task: str
    routing: RoutingPlan
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionMessage:
    """Message containing execution results."""

    task: str
    outcome: ExecutionOutcome
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProgressMessage:
    """Message containing progress evaluation."""

    task: str
    result: str
    progress: ProgressReport
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QualityMessage:
    """Message containing quality assessment."""

    task: str
    result: str
    quality: QualityReport
    routing: RoutingDecision | None = None  # Routing decision for final result
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JudgeMessage:
    """Message containing judge evaluation."""

    task: str
    result: str
    score: float
    refinement_needed: bool
    missing_elements: str
    refinement_agent: str | None = None
    improvements: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RefinementMessage:
    """Message requesting refinement of results."""

    task: str
    current_result: str
    judge_evaluation: JudgeMessage
    round_number: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinalResultMessage:
    """Final workflow result message."""

    result: str
    routing: RoutingDecision
    quality: QualityReport
    judge_evaluations: list[dict[str, Any]]
    execution_summary: dict[str, Any]
    phase_timings: dict[str, float]
    phase_status: dict[str, str]
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Streaming Events (from execution/streaming_events.py)
# =============================================================================


class MagenticAgentMessageEvent(WorkflowEvent):
    """Event wrapper for agent messages.

    Inherits from WorkflowEvent to ensure events added via ctx.add_event()
    are properly surfaced through the workflow's run_stream() output.
    """

    def __init__(
        self,
        agent_id: str,
        message: ChatMessage,
        stage: str | None = None,
        event: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the agent message event.

        Args:
            agent_id: The ID of the agent that produced this message.
            message: The ChatMessage content.
            stage: The workflow stage (e.g., 'execution').
            event: The event type (e.g., 'agent.start', 'agent.output').
            payload: Additional event metadata.
        """
        # Initialize parent with data for serialization
        super().__init__(data={"agent_id": agent_id})
        self.agent_id = agent_id
        self.message = message
        self.stage = stage
        self.event = event
        self.payload = payload or {}

    def __repr__(self) -> str:
        """Return a string representation of the event."""
        return (
            f"MagenticAgentMessageEvent(agent_id={self.agent_id!r}, "
            f"event={self.event!r}, stage={self.stage!r})"
        )


@dataclass(slots=True)
class StreamMetadata:
    """Metadata describing a streaming event."""

    stage: str
    event: str
    agent: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReasoningStreamEvent:
    """Event for streaming GPT-5 verbose reasoning tokens.

    This event type captures reasoning/chain-of-thought output from
    GPT-5 series models separately from the main response content.

    Attributes:
        reasoning: The reasoning text delta.
        agent_id: The agent that produced this reasoning (if applicable).
        is_complete: Whether this marks the end of reasoning output.
    """

    reasoning: str
    agent_id: str | None = None
    is_complete: bool = False


def _attach_metadata(
    event: MagenticAgentMessageEvent, metadata: StreamMetadata
) -> MagenticAgentMessageEvent:
    """Attach stage/event metadata to Magentic events (best-effort)."""

    event.stage = metadata.stage  # type: ignore[attr-defined]
    event.event = metadata.event  # type: ignore[attr-defined]
    event.payload = metadata.payload  # type: ignore[attr-defined]
    if metadata.agent and getattr(event, "agent_id", None) is None:
        event.agent_id = metadata.agent
    return event


def create_agent_event(
    *,
    stage: str,
    event: str,
    agent: str,
    text: str,
    payload: StreamPayload | None = None,
) -> MagenticAgentMessageEvent:
    """Build a structured MagenticAgentMessageEvent for agent activity."""

    message = ChatMessage(role=Role.ASSISTANT, text=text)
    metadata = StreamMetadata(stage=stage, event=event, agent=agent, payload=dict(payload or {}))
    return _attach_metadata(
        MagenticAgentMessageEvent(agent_id=agent or "unknown", message=message), metadata
    )


def create_system_event(
    *,
    stage: str,
    event: str,
    text: str,
    payload: StreamPayload | None = None,
    agent: str | None = None,
) -> MagenticAgentMessageEvent:
    """Build a structured event for non-agent/system updates."""

    message = ChatMessage(role=Role.ASSISTANT, text=text)
    metadata = StreamMetadata(stage=stage, event=event, agent=agent, payload=dict(payload or {}))
    return _attach_metadata(
        MagenticAgentMessageEvent(agent_id=agent or "system", message=message), metadata
    )
