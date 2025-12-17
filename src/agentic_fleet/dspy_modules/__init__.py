"""DSPy module package: signatures, reasoner wrappers, and lifecycle management.

This package contains DSPy signature definitions and the DSPyReasoner class
that provides intelligent task analysis, routing, and quality assessment using
DSPy's optimization capabilities.

Public API:
    - DSPyReasoner: Main reasoner class with DSPy integration
    - Signature classes: TaskAnalysis, TaskRouting, QualityAssessment, etc.
    - Handoff signatures: HandoffDecision, HandoffProtocol, etc.
    - Reasoning modules: FleetReAct, FleetPoT
    - Lifecycle management: configure_dspy_settings, get_dspy_lm, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_fleet.dspy_modules.handoff_signatures import HandoffDecision, HandoffProtocol
    from agentic_fleet.dspy_modules.lifecycle import (
        configure_dspy_settings,
        get_current_lm,
        get_dspy_lm,
        get_reflection_lm,
        reset_dspy_manager,
    )
    from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
    from agentic_fleet.dspy_modules.signatures import (
        AgentInstructionSignature,
        EnhancedTaskRouting,
        FleetPoT,
        FleetReAct,
        PlannerInstructionSignature,
        ProgressEvaluation,
        QualityAssessment,
        TaskAnalysis,
        TaskRouting,
        ToolAwareTaskAnalysis,
        WorkflowStrategy,
    )

__all__ = [
    # Signatures
    "AgentInstructionSignature",
    # Reasoner
    "DSPyReasoner",
    "EnhancedTaskRouting",
    "FleetPoT",
    "FleetReAct",
    "HandoffDecision",
    "HandoffProtocol",
    "PlannerInstructionSignature",
    "ProgressEvaluation",
    "QualityAssessment",
    "TaskAnalysis",
    "TaskRouting",
    "ToolAwareTaskAnalysis",
    "WorkflowStrategy",
    # Lifecycle management
    "configure_dspy_settings",
    "get_current_lm",
    "get_dspy_lm",
    "get_reflection_lm",
    "reset_dspy_manager",
]


def __getattr__(name: str) -> object:
    """Lazy import for public API."""
    # Lifecycle management
    if name in (
        "configure_dspy_settings",
        "get_current_lm",
        "get_dspy_lm",
        "get_reflection_lm",
        "reset_dspy_manager",
    ):
        from agentic_fleet.dspy_modules.lifecycle import (
            configure_dspy_settings,
            get_current_lm,
            get_dspy_lm,
            get_reflection_lm,
            reset_dspy_manager,
        )

        return {
            "configure_dspy_settings": configure_dspy_settings,
            "get_current_lm": get_current_lm,
            "get_dspy_lm": get_dspy_lm,
            "get_reflection_lm": get_reflection_lm,
            "reset_dspy_manager": reset_dspy_manager,
        }[name]

    if name == "DSPyReasoner":
        from agentic_fleet.dspy_modules.reasoner import DSPyReasoner

        return DSPyReasoner

    if name in (
        "AgentInstructionSignature",
        "EnhancedTaskRouting",
        "FleetPoT",
        "FleetReAct",
        "PlannerInstructionSignature",
        "ProgressEvaluation",
        "QualityAssessment",
        "TaskAnalysis",
        "TaskRouting",
        "ToolAwareTaskAnalysis",
        "WorkflowStrategy",
    ):
        from agentic_fleet.dspy_modules.signatures import (
            AgentInstructionSignature,
            EnhancedTaskRouting,
            FleetPoT,
            FleetReAct,
            PlannerInstructionSignature,
            ProgressEvaluation,
            QualityAssessment,
            TaskAnalysis,
            TaskRouting,
            ToolAwareTaskAnalysis,
            WorkflowStrategy,
        )

        return {
            "AgentInstructionSignature": AgentInstructionSignature,
            "EnhancedTaskRouting": EnhancedTaskRouting,
            "FleetPoT": FleetPoT,
            "FleetReAct": FleetReAct,
            "PlannerInstructionSignature": PlannerInstructionSignature,
            "ProgressEvaluation": ProgressEvaluation,
            "QualityAssessment": QualityAssessment,
            "TaskAnalysis": TaskAnalysis,
            "TaskRouting": TaskRouting,
            "ToolAwareTaskAnalysis": ToolAwareTaskAnalysis,
            "WorkflowStrategy": WorkflowStrategy,
        }[name]

    if name in ("HandoffDecision", "HandoffProtocol"):
        from agentic_fleet.dspy_modules.handoff_signatures import HandoffDecision, HandoffProtocol

        return HandoffDecision if name == "HandoffDecision" else HandoffProtocol

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
