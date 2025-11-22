"""Typed message dataclasses for fleet workflow executors.

These messages flow between executors in the agent-framework workflow,
providing type-safe communication between phases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..utils.models import RoutingDecision
from .models import (
    AnalysisResult,
    ExecutionOutcome,
    ProgressReport,
    QualityReport,
    RoutingPlan,
)


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
