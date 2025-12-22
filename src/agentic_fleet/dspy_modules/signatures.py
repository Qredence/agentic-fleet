"""DSPy signatures for agentic fleet.

This module defines the input/output signatures used by the DSPyReasoner
to perform cognitive tasks.

Refactored to enforce Pydantic-based typed signatures for all operations.
"""

from __future__ import annotations

import dspy

from .typed_models import (
    ProgressEvaluationOutput,
    QualityAssessmentOutput,
    RoutingDecisionOutput,
    TaskAnalysisOutput,
    ToolPlanOutput,
    WorkflowStrategyOutput,
)


class TaskAnalysis(dspy.Signature):
    """Analyze a task with structured output.

    Returns a validated TaskAnalysisOutput with type-safe fields.
    """

    task: str = dspy.InputField(desc="The user's task description")
    analysis: TaskAnalysisOutput = dspy.OutputField(
        desc="Structured analysis of the task including complexity, capabilities, and tool needs"
    )


class TaskRouting(dspy.Signature):
    """Route a task to agents with structured output.

    CRITICAL: Assign the minimum necessary agents to complete the task efficiently.
    Do not over-assign. For simple tasks, a single agent is preferred.

    Returns a validated RoutingDecisionOutput with type-safe fields.
    """

    task: str = dspy.InputField(desc="The task to route")
    team: str = dspy.InputField(desc="Description of available agents")
    context: str = dspy.InputField(desc="Optional execution context")
    current_date: str = dspy.InputField(desc="Current date for time-sensitive decisions")

    decision: RoutingDecisionOutput = dspy.OutputField(
        desc="Structured routing decision with agents, mode, subtasks, and tools"
    )


class EnhancedTaskRouting(dspy.Signature):
    """Advanced task routing with structured output.

    Optimizes for latency and token usage by pre-planning tool usage
    and setting execution constraints.

    Returns a validated RoutingDecisionOutput with all routing fields.
    """

    task: str = dspy.InputField(desc="Task to be routed")
    team_capabilities: str = dspy.InputField(desc="Capabilities of available agents")
    available_tools: str = dspy.InputField(desc="List of available tools")
    current_context: str = dspy.InputField(desc="Execution context")
    handoff_history: str = dspy.InputField(desc="History of agent handoffs")
    workflow_state: str = dspy.InputField(desc="Current state of the workflow")

    decision: RoutingDecisionOutput = dspy.OutputField(
        desc="Complete routing decision with agents, mode, tools, and strategy"
    )


class QualityAssessment(dspy.Signature):
    """Assess result quality with structured output.

    Returns a validated QualityAssessmentOutput with score and feedback.
    """

    task: str = dspy.InputField(desc="The original task")
    result: str = dspy.InputField(desc="The result produced by the agent")

    assessment: QualityAssessmentOutput = dspy.OutputField(
        desc="Quality assessment with score (0-10), missing elements, and improvements"
    )


class ProgressEvaluation(dspy.Signature):
    """Evaluate progress with structured output.

    Returns a validated ProgressEvaluationOutput with action and feedback.
    """

    task: str = dspy.InputField(desc="The original task")
    result: str = dspy.InputField(desc="The current result")

    evaluation: ProgressEvaluationOutput = dspy.OutputField(
        desc="Progress evaluation with action (complete/refine/continue) and feedback"
    )


class ToolPlan(dspy.Signature):
    """Generate tool plan with structured output.

    Returns a validated ToolPlanOutput with ordered tool list.
    """

    task: str = dspy.InputField(desc="The task to execute")
    available_tools: str = dspy.InputField(desc="List of available tools")

    plan: ToolPlanOutput = dspy.OutputField(
        desc="Tool plan with ordered list of tools and reasoning"
    )


class WorkflowStrategy(dspy.Signature):
    """Select workflow strategy with structured output.

    Selects between:
    - 'handoff': For simple, linear, or real-time tasks (Low latency).
    - 'standard': For complex, multi-step, or quality-critical tasks (High robustness).
    - 'fast_path': For trivial queries (Instant).

    Returns a validated WorkflowStrategyOutput.
    """

    task: str = dspy.InputField(desc="The user's request or task")
    complexity_analysis: str = dspy.InputField(desc="Analysis of task complexity")

    strategy: WorkflowStrategyOutput = dspy.OutputField(
        desc="Workflow strategy with mode (handoff/standard/fast_path) and reasoning"
    )


class SimpleResponse(dspy.Signature):
    """Directly answer a simple task or query."""

    task: str = dspy.InputField(desc="The simple task or question")
    answer: str = dspy.OutputField(desc="Concise and accurate answer")


class GroupChatSpeakerSelection(dspy.Signature):
    """Select the next speaker in a group chat."""

    history: str = dspy.InputField(desc="The conversation history so far")
    participants: str = dspy.InputField(desc="List of available participants and their roles")
    last_speaker: str = dspy.InputField(desc="The name of the last speaker")

    next_speaker: str = dspy.OutputField(desc="The name of the next speaker, or 'TERMINATE' to end")
    reasoning: str = dspy.OutputField(desc="Reasoning for the selection")


class AgentInstructionSignature(dspy.Signature):
    """Generate instructions for an agent based on its role and context."""

    role: str = dspy.InputField(desc="The role of the agent (e.g., 'coder', 'researcher')")
    description: str = dspy.InputField(desc="Description of the agent's responsibilities")
    task_context: str = dspy.InputField(desc="Context of the current task or workflow")

    agent_instructions: str = dspy.OutputField(desc="Detailed system instructions for the agent")


class PlannerInstructionSignature(dspy.Signature):
    """Generate specialized instructions for the Planner/Orchestrator agent."""

    available_agents: str = dspy.InputField(desc="List of available agents and their descriptions")
    workflow_goal: str = dspy.InputField(desc="The goal of the current workflow")

    agent_instructions: str = dspy.OutputField(desc="Detailed instructions for the Planner agent")


class WorkflowNarration(dspy.Signature):
    """Transform raw workflow events into a user-friendly narrative."""

    events_log: str = dspy.InputField(desc="Chronological log of workflow events")
    narrative: str = dspy.OutputField(
        desc="Concise, natural language summary of the workflow execution"
    )


# Backward-compatible aliases
TypedQualityAssessment = QualityAssessment
TypedEnhancedRouting = EnhancedTaskRouting
TypedToolPlan = ToolPlan
TypedProgressEvaluation = ProgressEvaluation
TypedTaskAnalysis = TaskAnalysis
TypedWorkflowStrategy = WorkflowStrategy


__all__ = [
    "AgentInstructionSignature",
    "EnhancedTaskRouting",
    "GroupChatSpeakerSelection",
    "PlannerInstructionSignature",
    "ProgressEvaluation",
    "QualityAssessment",
    "SimpleResponse",
    "TaskAnalysis",
    "TaskRouting",
    "ToolPlan",
    "TypedEnhancedRouting",
    "TypedProgressEvaluation",
    "TypedQualityAssessment",
    "TypedTaskAnalysis",
    "TypedToolPlan",
    "TypedWorkflowStrategy",
    "WorkflowNarration",
    "WorkflowStrategy",
]
