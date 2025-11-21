"""DSPy module package: signatures and reasoner wrappers.

This package contains DSPy signature definitions and the DSPyReasoner class
that provides intelligent task analysis, routing, and quality assessment using
DSPy's optimization capabilities.

Public API:
    - DSPyReasoner: Main reasoner class with DSPy integration
    - Signature classes: TaskAnalysis, TaskRouting, QualityAssessment, etc.
    - Handoff signatures: HandoffDecision, HandoffProtocol, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_fleet.dspy_modules.handoff_signatures import HandoffDecision, HandoffProtocol
    from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
    from agentic_fleet.dspy_modules.signatures import (
        ProgressEvaluation,
        QualityAssessment,
        TaskAnalysis,
        TaskRouting,
        ToolAwareTaskAnalysis,
    )

__all__ = [
    "DSPyReasoner",
    "HandoffDecision",
    "HandoffProtocol",
    "ProgressEvaluation",
    "QualityAssessment",
    "TaskAnalysis",
    "TaskRouting",
    "ToolAwareTaskAnalysis",
]


def __getattr__(name: str) -> object:
    """Lazy import for public API."""
    if name == "DSPyReasoner":
        from agentic_fleet.dspy_modules.reasoner import DSPyReasoner

        return DSPyReasoner

    if name == "DSPyReasoner":
        # Backward compatibility
        from agentic_fleet.dspy_modules.reasoner import DSPyReasoner

        return DSPyReasoner

    if name in (
        "TaskAnalysis",
        "TaskRouting",
        "ToolAwareTaskAnalysis",
        "ProgressEvaluation",
        "QualityAssessment",
    ):
        from agentic_fleet.dspy_modules.signatures import (
            ProgressEvaluation,
            QualityAssessment,
            TaskAnalysis,
            TaskRouting,
            ToolAwareTaskAnalysis,
        )

        if name == "TaskAnalysis":
            return TaskAnalysis
        if name == "TaskRouting":
            return TaskRouting
        if name == "ToolAwareTaskAnalysis":
            return ToolAwareTaskAnalysis
        if name == "ProgressEvaluation":
            return ProgressEvaluation
        return QualityAssessment

    if name in ("HandoffDecision", "HandoffProtocol"):
        from agentic_fleet.dspy_modules.handoff_signatures import HandoffDecision, HandoffProtocol

        if name == "HandoffDecision":
            return HandoffDecision
        return HandoffProtocol

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
