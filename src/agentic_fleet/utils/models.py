"""Shared data models and enums used across the agent framework."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any


class ExecutionMode(str, Enum):
    """Enumeration of supported execution modes within the workflow."""

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    DELEGATED = "delegated"
    GROUP_CHAT = "group_chat"
    DISCUSSION = "discussion"
    AUTO = "auto"
    HANDOFF = "handoff"

    @classmethod
    def from_raw(cls, value: Any) -> ExecutionMode:
        """Convert an arbitrary value into a valid ``ExecutionMode`` member."""

        if isinstance(value, ExecutionMode):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if member.value == normalized:
                    return member

        # Fallback to delegated (safest option if value is unknown)
        return cls.DELEGATED


class TaskStatus(str, Enum):
    """Status of a task execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRole(str, Enum):
    """Role of an agent in the fleet."""

    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    REVIEWER = "reviewer"
    CODER = "coder"
    PLANNER = "planner"


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool_name: str
    success: bool
    output: Any
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a task execution."""

    task_id: str
    status: TaskStatus
    result: Any
    agent_used: str
    execution_time: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Message exchanged between agents."""

    role: str
    content: str
    agent_name: str | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """State of the workflow."""

    task: str
    execution_mode: ExecutionMode
    current_agent: str | None
    iteration: int
    status: TaskStatus
    results: list[TaskResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingDecision:
    """Typed representation of a routing decision emitted by DSPy."""

    task: str
    assigned_to: tuple[str, ...]
    mode: ExecutionMode
    subtasks: tuple[str, ...] = field(default_factory=tuple)
    tool_requirements: tuple[str, ...] = field(default_factory=tuple)
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the routing decision into a JSON-serialisable dictionary."""

        return {
            "task": self.task,
            "assigned_to": list(self.assigned_to),
            "mode": self.mode.value,
            "subtasks": list(self.subtasks),
            "tool_requirements": list(self.tool_requirements),
            "confidence": self.confidence,
        }

    def update(self, **overrides: Any) -> RoutingDecision:
        """Return a new instance with one or more fields replaced."""

        return replace(self, **overrides)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> RoutingDecision:
        """Construct a routing decision from a mapping/dictionary."""

        task = str(value.get("task", "")).strip()
        assigned_to = tuple(_clean_iterable(value.get("assigned_to", [])))
        mode = ExecutionMode.from_raw(value.get("mode"))
        subtasks = tuple(_clean_iterable(value.get("subtasks", [])))
        tool_requirements = tuple(_clean_iterable(value.get("tool_requirements", [])))
        confidence = value.get("confidence")
        try:
            confidence_val = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence_val = None

        return cls(
            task=task,
            assigned_to=assigned_to,
            mode=mode,
            subtasks=subtasks,
            tool_requirements=tool_requirements,
            confidence=confidence_val,
        )


def ensure_routing_decision(
    value: RoutingDecision | Mapping[str, Any],
) -> RoutingDecision:
    """Coerce a value into a :class:`RoutingDecision` instance."""

    if isinstance(value, RoutingDecision):
        return value

    if isinstance(value, MutableMapping):
        return RoutingDecision.from_mapping(value)

    if isinstance(value, Mapping):
        return RoutingDecision.from_mapping(dict(value))

    raise TypeError(
        "Routing decisions must be provided as a Mapping or RoutingDecision instance; "
        f"got {type(value)!r}."
    )


def _clean_iterable(value: Sequence[str] | Iterable[str] | Any) -> list[str]:
    """Normalise an arbitrary iterable of strings."""

    if isinstance(value, str):
        return [value.strip()] if value.strip() else []

    if isinstance(value, Iterable):
        cleaned: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned

    return []
