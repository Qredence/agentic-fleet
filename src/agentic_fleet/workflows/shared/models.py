from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...utils.models import ExecutionMode, RoutingDecision


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
