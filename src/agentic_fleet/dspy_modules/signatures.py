"""DSPy signatures for agentic fleet.

This module defines the input/output signatures used by the DSPyReasoner
to perform cognitive tasks.

Consolidated from:
- signatures.py (core signatures)
- agent_signatures.py (agent instruction generation)
- workflow_signatures.py (enhanced routing and workflow strategy)

DSPy 3.x Note:
Signatures now support Pydantic models as output field types for structured
outputs. Typed signatures (prefixed with 'Typed') use Pydantic models to
enforce JSON schema compliance and enable automatic validation/retry.
"""

from __future__ import annotations

from typing import Any, Literal

import dspy

from .typed_models import (
    ProgressEvaluationOutput,
    QualityAssessmentOutput,
    RoutingDecisionOutput,
    TaskAnalysisOutput,
    ToolPlanOutput,
    WorkflowStrategyOutput,
)

# =============================================================================
# Core Task Signatures
# =============================================================================


class TaskAnalysis(dspy.Signature):
    """Analyze a task to understand its requirements and complexity."""

    task: str = dspy.InputField(desc="The user's task description")

    complexity: Literal["low", "medium", "high"] = dspy.OutputField(desc="Estimated complexity")
    required_capabilities: list[str] = dspy.OutputField(
        desc="List of required capabilities (e.g., research, coding)"
    )
    estimated_steps: int = dspy.OutputField(desc="Estimated number of steps")
    preferred_tools: list[str] = dspy.OutputField(
        desc="Ordered list of tools to prioritize if needed (use tool names)"
    )
    needs_web_search: bool = dspy.OutputField(
        desc="True if the task requires fresh or online information"
    )
    search_query: str = dspy.OutputField(
        desc="Suggested search query (empty string if web search is not needed)"
    )
    urgency: Literal["low", "medium", "high"] = dspy.OutputField(
        desc="Time sensitivity / freshness requirement"
    )
    reasoning: str = dspy.OutputField(desc="Reasoning behind the analysis")


class TaskRouting(dspy.Signature):
    """Route a task to the appropriate agent(s).

    Instruct agents (especially Researcher) to use search tools like Tavily when
    queries are time-sensitive or require current information.

    CRITICAL: Assign the minimum necessary agents to complete the task efficiently.
    Do not over-assign. For simple tasks, a single agent is preferred.
    """

    task: str = dspy.InputField(desc="The task to route")
    team: str = dspy.InputField(desc="Description of available agents")
    context: str = dspy.InputField(desc="Optional execution context")
    current_date: str = dspy.InputField(desc="Current date to inform time-sensitive decisions")

    assigned_to: list[str] = dspy.OutputField(desc="List of agent names assigned to the task")
    mode: Literal["delegated", "sequential", "parallel"] = dspy.OutputField(desc="Execution mode")
    subtasks: list[str] = dspy.OutputField(desc="List of subtasks (if applicable)")
    tool_requirements: list[str] = dspy.OutputField(desc="List of required tool names (if any)")
    reasoning: str = dspy.OutputField(desc="Reasoning for the routing decision")


class ToolAwareTaskAnalysis(TaskAnalysis):
    """Extended analysis that considers available tools."""

    available_tools: str = dspy.InputField(desc="List of available tools")


class QualityAssessment(dspy.Signature):
    """Assess the quality of a task result."""

    task: str = dspy.InputField(desc="The original task")
    result: str = dspy.InputField(desc="The result produced by the agent")

    score: float = dspy.OutputField(desc="Quality score between 0.0 and 10.0")
    missing_elements: str = dspy.OutputField(desc="Description of what is missing")
    required_improvements: str = dspy.OutputField(desc="Specific improvements needed")
    reasoning: str = dspy.OutputField(desc="Reasoning for the score")


class ProgressEvaluation(dspy.Signature):
    """Evaluate progress and decide next steps."""

    task: str = dspy.InputField(desc="The original task")
    result: str = dspy.InputField(desc="The current result")

    action: Literal["complete", "refine", "continue"] = dspy.OutputField(desc="Next action to take")
    feedback: str = dspy.OutputField(desc="Feedback for the next step")
    reasoning: str = dspy.OutputField(desc="Reasoning for the decision")


class ToolPlan(dspy.Signature):
    """Generate a high-level plan for tool usage."""

    task: str = dspy.InputField(desc="The task to execute")
    available_tools: str = dspy.InputField(desc="List of available tools")

    tool_plan: list[str] = dspy.OutputField(desc="Ordered list of tool names to use")
    reasoning: str = dspy.OutputField(desc="Reasoning for the plan")


class SimpleResponse(dspy.Signature):
    """Directly answer a simple task or query."""

    task: str = dspy.InputField(desc="The simple task or question")
    answer: str = dspy.OutputField(desc="Concise and accurate answer")


# NOTE: JudgeEvaluation signature removed in Plan #4 optimization
# Quality assessment is now handled solely by QualityAssessment signature


class GroupChatSpeakerSelection(dspy.Signature):
    """Select the next speaker in a group chat."""

    history: str = dspy.InputField(desc="The conversation history so far")
    participants: str = dspy.InputField(desc="List of available participants and their roles")
    last_speaker: str = dspy.InputField(desc="The name of the last speaker")

    next_speaker: str = dspy.OutputField(desc="The name of the next speaker, or 'TERMINATE' to end")
    reasoning: str = dspy.OutputField(desc="Reasoning for the selection")


# =============================================================================
# Agent Instruction Signatures (from agent_signatures.py)
# =============================================================================


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


# =============================================================================
# Workflow-specific Signatures (from workflow_signatures.py)
# =============================================================================


class EnhancedTaskRouting(dspy.Signature):
    """Advanced task routing with efficiency and tool-planning awareness.

    Optimizes for latency and token usage by pre-planning tool usage
    and setting execution constraints.
    """

    task: str = dspy.InputField(desc="Task to be routed")
    team_capabilities: str = dspy.InputField(desc="Capabilities of available agents")
    available_tools: str = dspy.InputField(desc="List of available tools")
    current_context: str = dspy.InputField(desc="Execution context")
    handoff_history: str = dspy.InputField(desc="History of agent handoffs")
    workflow_state: str = dspy.InputField(desc="Current state of the workflow")

    assigned_to: list[str] = dspy.OutputField(desc="Agents assigned to the task")
    execution_mode: Literal["delegated", "sequential", "parallel"] = dspy.OutputField(
        desc="Execution mode"
    )
    subtasks: list[str] = dspy.OutputField(desc="Breakdown of subtasks")

    handoff_strategy: str = dspy.OutputField(desc="Strategy for agent handoffs")
    workflow_gates: str = dspy.OutputField(desc="Quality gates and checkpoints")

    # Efficiency and Tool Planning Fields
    tool_plan: list[str] = dspy.OutputField(desc="Ordered list of tools to use")
    tool_goals: str = dspy.OutputField(desc="Specific goals for tool usage")
    latency_budget: str = dspy.OutputField(desc="Estimated time/latency budget")
    reasoning: str = dspy.OutputField(desc="Reasoning for the routing decision")


class WorkflowStrategy(dspy.Signature):
    """Decides the high-level workflow architecture for a task.

    Selects between:
    - 'handoff': For simple, linear, or real-time tasks (Low latency).
    - 'standard': For complex, multi-step, or quality-critical tasks (High robustness).
    - 'fast_path': For trivial queries (Instant).
    """

    task: str = dspy.InputField(desc="The user's request or task")
    complexity_analysis: str = dspy.InputField(desc="Analysis of task complexity")

    workflow_mode: Literal["handoff", "standard", "fast_path"] = dspy.OutputField(
        desc="The optimal workflow architecture"
    )
    reasoning: str = dspy.OutputField(desc="Why this architecture was chosen")


# =============================================================================
# Advanced Reasoning Modules (from reasoning.py)
# =============================================================================


class FleetReAct(dspy.Module):
    """ReAct (Reason + Act) module for autonomous tool usage.

    Configures ReAct with appropriate max_iters to balance between
    thoroughness and latency/cost. Default max_iters=5 provides good
    coverage while preventing infinite loops.

    Args:
        signature: DSPy signature defining input/output format
        tools: List of tools available for the ReAct agent to use
        max_iters: Maximum number of ReAct iterations to prevent infinite loops.
                   Default is 5 to balance thoroughness with latency/cost.
    """

    def __init__(
        self, signature: Any = None, tools: list[Any] | None = None, max_iters: int = 5
    ) -> None:
        """
        Initialize a FleetReAct reasoning module that runs a ReAct loop with the given signature, tools, and iteration limit.

        Parameters:
            signature (Any): Signature or signature string describing the expected input→output mapping for the ReAct instance (e.g., "question -> answer").
            tools (list[Any] | None): Optional list of tool objects available to the ReAct loop.
            max_iters (int): Maximum number of ReAct iterations to execute.
        """
        super().__init__()
        sig_arg = signature or "question -> answer"
        self.react = dspy.ReAct(sig_arg, tools=tools or [], max_iters=max_iters)  # type: ignore[arg-type]
        self.max_iters = max_iters

    def forward(self, question: str, tools: list[Any] | None = None) -> dspy.Prediction:
        """
        Run the ReAct reasoning loop for a given question.

        Parameters:
            question (str): The question or task to solve.
            tools (list[Any] | None): Optional tools to expose to the ReAct loop; if omitted, the instance's configured tools are used.

        Returns:
            dspy.Prediction: Prediction containing the final answer and reasoning trace.
        """
        return self.react(question=question, tools=tools)


class FleetPoT(dspy.Module):
    """Program of Thought module for code-based reasoning."""

    def __init__(self, signature: Any = None) -> None:
        super().__init__()
        self.pot = dspy.ProgramOfThought(signature or "question -> answer")
        self.last_error: str | None = None

    def forward(self, question: str) -> dspy.Prediction:
        """
        Run the Program of Thought on a question and return the resulting prediction.

        Clears `last_error` before execution. If a `RuntimeError` occurs, stores its message in `last_error` and re-raises the exception.

        Parameters:
            question (str): The question or task to solve.

        Returns:
            dspy.Prediction: Prediction containing the answer and reasoning (code).
        """
        self.last_error = None
        try:
            result = self.pot(question=question)
        except RuntimeError as exc:
            self.last_error = str(exc)
            raise
        return result


# =============================================================================
# Typed Signatures (DSPy 3.x with Pydantic models)
# =============================================================================
# These signatures use Pydantic models for structured outputs, providing:
# - JSON schema compliance enforcement
# - Automatic validation and type coercion
# - Better error messages on parse failures
# - Field-level constraints (min/max, enums, etc.)


class TypedTaskAnalysis(dspy.Signature):
    """Analyze a task with structured output.

    Returns a validated TaskAnalysisOutput with type-safe fields.
    """

    task: str = dspy.InputField(desc="The user's task description")
    analysis: TaskAnalysisOutput = dspy.OutputField(
        desc="Structured analysis of the task including complexity, capabilities, and tool needs"
    )


class TypedTaskRouting(dspy.Signature):
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


class TypedEnhancedRouting(dspy.Signature):
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


class TypedQualityAssessment(dspy.Signature):
    """Assess result quality with structured output.

    Returns a validated QualityAssessmentOutput with score and feedback.
    """

    task: str = dspy.InputField(desc="The original task")
    result: str = dspy.InputField(desc="The result produced by the agent")

    assessment: QualityAssessmentOutput = dspy.OutputField(
        desc="Quality assessment with score (0-10), missing elements, and improvements"
    )


class TypedProgressEvaluation(dspy.Signature):
    """Evaluate progress with structured output.

    Returns a validated ProgressEvaluationOutput with action and feedback.
    """

    task: str = dspy.InputField(desc="The original task")
    result: str = dspy.InputField(desc="The current result")

    evaluation: ProgressEvaluationOutput = dspy.OutputField(
        desc="Progress evaluation with action (complete/refine/continue) and feedback"
    )


class TypedToolPlan(dspy.Signature):
    """Generate tool plan with structured output.

    Returns a validated ToolPlanOutput with ordered tool list.
    """

    task: str = dspy.InputField(desc="The task to execute")
    available_tools: str = dspy.InputField(desc="List of available tools")

    plan: ToolPlanOutput = dspy.OutputField(
        desc="Tool plan with ordered list of tools and reasoning"
    )


class TypedWorkflowStrategy(dspy.Signature):
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


class WorkflowNarration(dspy.Signature):
    """Transform raw workflow events into a user-friendly narrative."""

    events_log: str = dspy.InputField(desc="Chronological log of workflow events")
    narrative: str = dspy.OutputField(
        desc="Concise, natural language summary of the workflow execution"
    )


# Export signatures (sorted alphabetically per ruff RUF022)
__all__ = [
    "AgentInstructionSignature",
    "EnhancedTaskRouting",
    "FleetPoT",
    "FleetReAct",
    "GroupChatSpeakerSelection",
    "PlannerInstructionSignature",
    "ProgressEvaluation",
    "QualityAssessment",
    "SimpleResponse",
    "TaskAnalysis",
    "TaskRouting",
    "ToolAwareTaskAnalysis",
    "ToolPlan",
    "TypedEnhancedRouting",
    "TypedProgressEvaluation",
    "TypedQualityAssessment",
    "TypedTaskAnalysis",
    "TypedTaskRouting",
    "TypedToolPlan",
    "TypedWorkflowStrategy",
    "WorkflowNarration",
    "WorkflowStrategy",
]
