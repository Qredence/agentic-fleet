"""DSPy programs facade.

Re-exports all DSPy signatures, modules, and reasoner from the dspy_modules package.
This provides a single import point for DSPy-related functionality.

Usage:
    from agentic_fleet.services.dspy_programs import DSPyReasoner, TaskAnalysis
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
# NLU Module (signatures now included in nlu.py)
# =============================================================================
from agentic_fleet.dspy_modules.nlu import (
    DSPyNLU,
    EntityExtraction,
    IntentClassification,
    get_nlu_module,
)

# =============================================================================
# Core Reasoner
# =============================================================================
from agentic_fleet.dspy_modules.reasoner import DSPyReasoner

# =============================================================================
# Handoff Signatures (now in signatures.py)
# =============================================================================
# =============================================================================
# Signatures - Task Analysis & Routing
# =============================================================================
# =============================================================================
# Reasoning Modules
# =============================================================================
from agentic_fleet.dspy_modules.signatures import (
    AgentInstructionSignature,
    EnhancedTaskRouting,
    HandoffDecision,
    HandoffProtocol,
    PlannerInstructionSignature,
    ProgressEvaluation,
    QualityAssessment,
    TaskAnalysis,
    TaskRouting,
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
