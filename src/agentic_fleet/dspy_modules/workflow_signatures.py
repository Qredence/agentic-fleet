"""
Enhanced DSPy signatures for Microsoft agent-framework workflow integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import dspy

if TYPE_CHECKING:  # pragma: no cover - typing helper

    class SignatureBase(Protocol):
        """Protocol version of dspy.Signature to keep mypy satisfied."""

        ...

    class _Field:
        def __init__(self, desc: str = ""): ...

    InputField = _Field
    OutputField = _Field
else:  # pragma: no cover - runtime path
    SignatureBase = dspy.Signature
    InputField = dspy.InputField
    OutputField = dspy.OutputField


class EnhancedTaskRouting(SignatureBase):
    """Advanced task routing with agent-framework workflow integration."""

    task = InputField(desc="task to be routed")
    team_capabilities = InputField(desc="available team members and their skills")
    available_tools = InputField(desc="available tools and their capabilities")
    current_context = InputField(desc="current workflow state and history")
    handoff_history = InputField(desc="recent handoff patterns and outcomes")
    workflow_state = InputField(desc="current agent-framework workflow state")

    assigned_to = OutputField(desc="primary agent(s) for initial work")
    execution_mode = OutputField(desc="delegated|sequential|parallel|adaptive")
    handoff_strategy = OutputField(desc="planned handoff checkpoints and triggers")
    subtasks = OutputField(desc="task breakdown with handoff points marked")
    workflow_gates = OutputField(desc="checkpoints requiring review before continuation")


class WorkflowHandoffDecision(SignatureBase):
    """DSPy signature for agent-framework handoff decisions."""

    current_workflow_state = InputField(desc="current agent-framework workflow state")
    agent_performance = InputField(desc="performance metrics for current agent")
    task_progress = InputField(desc="current task completion status")
    available_transitions = InputField(desc="possible handoff targets and conditions")

    should_handoff = OutputField(desc="yes/no decision for handoff")
    target_agent = OutputField(desc="which agent to transition to")
    handoff_context = OutputField(desc="context package for handoff")
    transition_strategy = OutputField(desc="how to execute the handoff")


class JudgeEvaluation(SignatureBase):
    """DSPy signature for structured judge evaluation with quality criteria."""

    task = InputField(desc="original task that was executed")
    result = InputField(desc="the result/output to be evaluated")
    quality_criteria = InputField(desc="specific quality criteria checklist to evaluate against")

    score = OutputField(desc="quality score from 0-10 reflecting completeness across all criteria")
    missing_elements = OutputField(
        desc="comma-separated list of missing elements: citations, vote_totals, dates, context"
    )
    required_improvements = OutputField(desc="specific instructions for what needs to be improved")
    refinement_agent = OutputField(
        desc="which agent should handle the refinement: Researcher, Analyst, or Writer"
    )
    refinement_needed = OutputField(desc="yes or no - whether refinement is needed")
