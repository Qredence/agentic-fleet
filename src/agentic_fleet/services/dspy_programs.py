"""DSPy programs facade.

Re-exports all DSPy signatures, modules, and reasoner from the dspy_modules package.
This provides a single import point for DSPy-related functionality.

Usage:
    from agentic_fleet.services.dspy_programs import DSPyReasoner, TaskAnalysis
    from agentic_fleet.services.dspy_programs import FleetReAct, FleetPoT
"""

from __future__ import annotations

# =============================================================================
# Answer Quality
# =============================================================================
from agentic_fleet.dspy_modules.answer_quality import AnswerQualitySignature

# =============================================================================
# Assertions (DSPy Assert/Suggest guards)
# =============================================================================
from agentic_fleet.dspy_modules.assertions import (
    assert_mode_agent_consistency,
    assert_valid_agents,
    assert_valid_tools,
    suggest_mode_agent_consistency,
    suggest_task_type_routing,
    suggest_valid_agents,
    suggest_valid_tools,
    validate_full_routing,
    validate_routing_decision,
    with_routing_assertions,
)

# =============================================================================
# Handoff Signatures
# =============================================================================
from agentic_fleet.dspy_modules.handoff_signatures import HandoffDecision, HandoffProtocol

# =============================================================================
# NLU Module
# =============================================================================
from agentic_fleet.dspy_modules.nlu import DSPyNLU, get_nlu_module

# =============================================================================
# NLU Signatures
# =============================================================================
from agentic_fleet.dspy_modules.nlu_signatures import (
    EntityExtraction,
    IntentClassification,
)

# =============================================================================
# Core Reasoner
# =============================================================================
from agentic_fleet.dspy_modules.reasoner import DSPyReasoner

# =============================================================================
# Signatures - Task Analysis & Routing
# =============================================================================
# =============================================================================
# Reasoning Modules
# =============================================================================
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

# =============================================================================
# Typed Models (Pydantic outputs for DSPy)
# =============================================================================
from agentic_fleet.dspy_modules.typed_models import (
    CapabilityMatchOutput,
    GroupChatSpeakerOutput,
    HandoffDecisionOutput,
    ProgressEvaluationOutput,
    QualityAssessmentOutput,
    RoutingDecisionOutput,
    SimpleResponseOutput,
    TaskAnalysisOutput,
    ToolPlanOutput,
    WorkflowStrategyOutput,
)

__all__ = [
    "AgentInstructionSignature",
    "AnswerQualitySignature",
    "CapabilityMatchOutput",
    "DSPyNLU",
    "DSPyReasoner",
    "EnhancedTaskRouting",
    "EntityExtraction",
    "FleetPoT",
    "FleetReAct",
    "GroupChatSpeakerOutput",
    "HandoffDecision",
    "HandoffDecisionOutput",
    "HandoffProtocol",
    "IntentClassification",
    "PlannerInstructionSignature",
    "ProgressEvaluation",
    "ProgressEvaluationOutput",
    "QualityAssessment",
    "QualityAssessmentOutput",
    "RoutingDecisionOutput",
    "SimpleResponseOutput",
    "TaskAnalysis",
    "TaskAnalysisOutput",
    "TaskRouting",
    "ToolAwareTaskAnalysis",
    "ToolPlanOutput",
    "WorkflowStrategy",
    "WorkflowStrategyOutput",
    # Assertion utilities
    "assert_mode_agent_consistency",
    "assert_valid_agents",
    "assert_valid_tools",
    "get_nlu_module",
    "suggest_mode_agent_consistency",
    "suggest_task_type_routing",
    "suggest_valid_agents",
    "suggest_valid_tools",
    "validate_full_routing",
    "validate_routing_decision",
    "with_routing_assertions",
]
