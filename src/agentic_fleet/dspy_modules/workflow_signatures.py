"""
Enhanced DSPy signatures for Microsoft agent-framework workflow integration.
"""

from __future__ import annotations

import dspy


class Dspy:
    class Signature:
        pass

        class InputField:
            def __init__(self, desc=""):
                self.desc = desc

        class OutputField:
            def __init__(self, desc=""):
                self.desc = desc


class EnhancedTaskRouting(dspy.Signature):
    """Advanced task routing with agent-framework workflow integration."""

    task = dspy.InputField(desc="task to be routed")
    team_capabilities = dspy.InputField(desc="available team members and their skills")
    available_tools = dspy.InputField(desc="available tools and their capabilities")
    current_context = dspy.InputField(desc="current workflow state and history")
    handoff_history = dspy.InputField(desc="recent handoff patterns and outcomes")
    workflow_state = dspy.InputField(desc="current agent-framework workflow state")

    assigned_to = dspy.OutputField(desc="primary agent(s) for initial work")
    execution_mode = dspy.OutputField(desc="delegated|sequential|parallel|adaptive")
    handoff_strategy = dspy.OutputField(desc="planned handoff checkpoints and triggers")
    subtasks = dspy.OutputField(desc="task breakdown with handoff points marked")
    workflow_gates = dspy.OutputField(desc="checkpoints requiring review before continuation")


class WorkflowHandoffDecision(dspy.Signature):
    """DSPy signature for agent-framework handoff decisions."""

    current_workflow_state = dspy.InputField(desc="current agent-framework workflow state")
    agent_performance = dspy.InputField(desc="performance metrics for current agent")
    task_progress = dspy.InputField(desc="current task completion status")
    available_transitions = dspy.InputField(desc="possible handoff targets and conditions")

    should_handoff = dspy.OutputField(desc="yes/no decision for handoff")
    target_agent = dspy.OutputField(desc="which agent to transition to")
    handoff_context = dspy.OutputField(desc="context package for handoff")
    transition_strategy = dspy.OutputField(desc="how to execute the handoff")


class JudgeEvaluation(dspy.Signature):
    """DSPy signature for structured judge evaluation with quality criteria."""

    task = dspy.InputField(desc="original task that was executed")
    result = dspy.InputField(desc="the result/output to be evaluated")
    quality_criteria = dspy.InputField(
        desc="specific quality criteria checklist to evaluate against"
    )

    score = dspy.OutputField(
        desc="quality score from 0-10 reflecting completeness across all criteria"
    )
    missing_elements = dspy.OutputField(
        desc="comma-separated list of missing elements: citations, vote_totals, dates, context"
    )
    required_improvements = dspy.OutputField(
        desc="specific instructions for what needs to be improved"
    )
    refinement_agent = dspy.OutputField(
        desc="which agent should handle the refinement: Researcher, Analyst, or Writer"
    )
    refinement_needed = dspy.OutputField(desc="yes or no - whether refinement is needed")
