"""DSPy signatures for agentic fleet.

This module defines the input/output signatures used by the DSPyReasoner
to perform cognitive tasks.
"""

from __future__ import annotations

from typing import Literal

import dspy


class TaskAnalysis(dspy.Signature):
    """Analyze a task to understand its requirements and complexity."""

    task: str = dspy.InputField(desc="The user's task description")

    complexity: Literal["low", "medium", "high"] = dspy.OutputField(desc="Estimated complexity")
    required_capabilities: list[str] = dspy.OutputField(
        desc="List of required capabilities (e.g., research, coding)"
    )
    estimated_steps: int = dspy.OutputField(desc="Estimated number of steps")
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


class JudgeEvaluation(dspy.Signature):
    """Detailed evaluation by a judge agent.

    If the task asks about a specific entity and the result correctly states that it does not exist or is not public,
    score this highly for accuracy. Do not penalize for missing 'features' of non-existent products.
    """

    task: str = dspy.InputField(desc="The original task")
    result: str = dspy.InputField(desc="The result to evaluate")
    criteria: str = dspy.InputField(desc="Evaluation criteria")

    score: float = dspy.OutputField(desc="Score between 0.0 and 10.0")
    refinement_needed: Literal["yes", "no"] = dspy.OutputField(desc="Whether refinement is needed")
    missing_elements: str = dspy.OutputField(desc="What is missing")
    required_improvements: str = dspy.OutputField(desc="What needs to be improved")
    refinement_agent: str = dspy.OutputField(desc="Agent best suited for refinement")
    reasoning: str = dspy.OutputField(desc="Detailed evaluation reasoning")
