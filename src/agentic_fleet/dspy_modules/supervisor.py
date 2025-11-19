"""DSPy-powered supervisor for intelligent orchestration.

This module implements the DSPySupervisor, which uses DSPy's language model
programming capabilities to perform high-level cognitive tasks:
- Task Analysis: Decomposing complex requests
- Routing: Assigning tasks to the best agents
- Quality Assessment: Evaluating results against criteria
- Progress Tracking: Monitoring execution state
- Tool Planning: Deciding which tools to use
"""

from __future__ import annotations

from typing import Any

import dspy

from ..utils.logger import setup_logger
from .signatures import (
    JudgeEvaluation,
    ProgressEvaluation,
    QualityAssessment,
    TaskAnalysis,
    TaskRouting,
    ToolPlan,
)

logger = setup_logger(__name__)


class DSPySupervisor:
    """Supervisor that uses DSPy modules for orchestration decisions."""

    def __init__(self, use_enhanced_signatures: bool = True) -> None:
        """Initialize the DSPy supervisor.

        Args:
            use_enhanced_signatures: Whether to use the new typed signatures (default: True)
        """
        self.use_enhanced_signatures = use_enhanced_signatures
        self._execution_history: list[dict[str, Any]] = []

        # Initialize DSPy modules
        # We use ChainOfThought for robust reasoning before outputting the structured result.
        self.analyzer = dspy.ChainOfThought(TaskAnalysis)
        self.router = dspy.ChainOfThought(TaskRouting)
        self.quality_assessor = dspy.ChainOfThought(QualityAssessment)
        self.progress_evaluator = dspy.ChainOfThought(ProgressEvaluation)
        self.tool_planner = dspy.ChainOfThought(ToolPlan)
        self.judge = dspy.ChainOfThought(JudgeEvaluation)

        self.tool_registry: Any | None = None

    def set_tool_registry(self, tool_registry: Any) -> None:
        """Attach a tool registry to the supervisor."""
        self.tool_registry = tool_registry

    def analyze_task(
        self, task: str, use_tools: bool = False, perform_search: bool = False
    ) -> dict[str, Any]:
        """Analyze a task to understand its requirements and complexity.

        Args:
            task: The user's task description
            use_tools: Whether to allow tool usage during analysis (default: False)
            perform_search: Whether to perform web search during analysis (default: False)

        Returns:
            Dictionary containing analysis results (complexity, capabilities, etc.)
        """
        logger.info(f"Analyzing task: {task[:100]}...")
        prediction = self.analyzer(task=task)

        # Extract fields from prediction
        # Typed signatures provide these directly as attributes
        return {
            "complexity": getattr(prediction, "complexity", "medium"),
            "required_capabilities": getattr(prediction, "required_capabilities", []),
            "estimated_steps": getattr(prediction, "estimated_steps", 1),
            "reasoning": getattr(prediction, "reasoning", ""),
        }

    def route_task(
        self,
        task: str,
        team: dict[str, str],
        context: str = "",
        handoff_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Route a task to the most appropriate agent(s).

        Args:
            task: The task to route
            team: Dictionary mapping agent names to their descriptions
            context: Optional context string
            handoff_history: Optional history of agent handoffs

        Returns:
            Dictionary containing routing decision (assigned_to, mode, subtasks)
        """
        logger.info(f"Routing task: {task[:100]}...")

        # Format team description
        team_str = "\n".join([f"- {name}: {desc}" for name, desc in team.items()])

        prediction = self.router(task=task, team=team_str, context=context)

        return {
            "task": task,
            "assigned_to": getattr(prediction, "assigned_to", []),
            "mode": getattr(prediction, "mode", "delegated"),
            "subtasks": getattr(prediction, "subtasks", [task]),
            "reasoning": getattr(prediction, "reasoning", ""),
        }

    def assess_quality(self, task: str = "", result: str = "", **kwargs: Any) -> dict[str, Any]:
        """Assess the quality of a task result.

        Args:
            task: The original task
            result: The result produced by the agent
            **kwargs: Compatibility arguments (requirements, results, etc.)

        Returns:
            Dictionary containing quality assessment (score, missing, improvements)
        """
        actual_task = task or kwargs.get("requirements", "")
        actual_result = result or kwargs.get("results", "")

        logger.info("Assessing result quality...")
        prediction = self.quality_assessor(task=actual_task, result=actual_result)

        return {
            "score": getattr(prediction, "score", 0.0),
            "missing": getattr(prediction, "missing_elements", ""),
            "improvements": getattr(prediction, "required_improvements", ""),
            "reasoning": getattr(prediction, "reasoning", ""),
        }

    def evaluate_progress(self, task: str = "", result: str = "", **kwargs: Any) -> dict[str, Any]:
        """Evaluate progress and decide next steps (complete or refine).

        Args:
            task: The original task
            result: The current result
            **kwargs: Compatibility arguments (original_task, completed, etc.)

        Returns:
            Dictionary containing progress evaluation (action, feedback)
        """
        # Handle parameter aliases from different executors
        actual_task = task or kwargs.get("original_task", "")
        actual_result = result or kwargs.get("completed", "")

        logger.info("Evaluating progress...")
        prediction = self.progress_evaluator(task=actual_task, result=actual_result)

        return {
            "action": getattr(prediction, "action", "complete"),
            "feedback": getattr(prediction, "feedback", ""),
            "reasoning": getattr(prediction, "reasoning", ""),
        }

    def decide_tools(
        self, task: str, team: dict[str, str], current_context: str = ""
    ) -> dict[str, Any]:
        """Decide which tools to use for a task (ReAct-style planning).

        Args:
            task: The task to execute
            team: Available agents/tools description
            current_context: Current execution context

        Returns:
            Dictionary containing tool plan
        """
        logger.info("Deciding tools...")

        team_str = "\n".join([f"- {name}: {desc}" for name, desc in team.items()])

        prediction = self.tool_planner(task=task, available_tools=team_str)

        return {
            "tool_plan": getattr(prediction, "tool_plan", []),
            "reasoning": getattr(prediction, "reasoning", ""),
        }

    def get_execution_summary(self) -> dict[str, Any]:
        """Return a summary of the execution history."""
        return {
            "history_count": len(self._execution_history),
            # Add more summary stats if needed
        }
