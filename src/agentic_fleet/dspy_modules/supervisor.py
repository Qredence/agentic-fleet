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

    def analyze_task(self, task: str) -> dict[str, Any]:
        """Analyze a task to understand its requirements and complexity.

        Args:
            task: The user's task description

        Returns:
            Dictionary containing analysis results (complexity, capabilities, etc.)
        """
        logger.info(f"Analyzing task: {task[:100]}...")
        try:
            prediction = self.analyzer(task=task)

            # Extract fields from prediction
            # Typed signatures provide these directly as attributes
            return {
                "complexity": getattr(prediction, "complexity", "medium"),
                "required_capabilities": getattr(prediction, "required_capabilities", []),
                "estimated_steps": getattr(prediction, "estimated_steps", 1),
                "reasoning": getattr(prediction, "reasoning", ""),
            }
        except Exception as e:
            logger.error(f"Task analysis failed: {e}")
            # Fallback
            return {
                "complexity": "medium",
                "required_capabilities": [],
                "estimated_steps": 1,
                "reasoning": "Analysis failed, using defaults.",
            }

    def route_task(self, task: str, team: dict[str, str], context: str = "") -> dict[str, Any]:
        """Route a task to the most appropriate agent(s).

        Args:
            task: The task to route
            team: Dictionary mapping agent names to their descriptions
            context: Optional context string

        Returns:
            Dictionary containing routing decision (assigned_to, mode, subtasks)
        """
        logger.info(f"Routing task: {task[:100]}...")

        # Format team description
        team_str = "\n".join([f"- {name}: {desc}" for name, desc in team.items()])

        try:
            prediction = self.router(task=task, team=team_str, context=context)

            return {
                "task": task,
                "assigned_to": getattr(prediction, "assigned_to", []),
                "mode": getattr(prediction, "mode", "delegated"),
                "subtasks": getattr(prediction, "subtasks", [task]),
                "reasoning": getattr(prediction, "reasoning", ""),
            }
        except Exception as e:
            logger.error(f"Task routing failed: {e}")
            # Fallback
            return {
                "task": task,
                "assigned_to": list(team.keys())[:1] if team else [],
                "mode": "delegated",
                "subtasks": [task],
                "reasoning": "Routing failed, using fallback.",
            }

    def assess_quality(self, task: str, result: str) -> dict[str, Any]:
        """Assess the quality of a task result.

        Args:
            task: The original task
            result: The result produced by the agent

        Returns:
            Dictionary containing quality assessment (score, missing, improvements)
        """
        logger.info("Assessing result quality...")
        try:
            prediction = self.quality_assessor(task=task, result=result)

            return {
                "score": getattr(prediction, "score", 0.0),
                "missing": getattr(prediction, "missing_elements", ""),
                "improvements": getattr(prediction, "required_improvements", ""),
                "reasoning": getattr(prediction, "reasoning", ""),
            }
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return {
                "score": 0.0,
                "missing": "Assessment failed",
                "improvements": "",
                "reasoning": str(e),
            }

    def evaluate_progress(self, task: str, result: str) -> dict[str, Any]:
        """Evaluate progress and decide next steps (complete or refine).

        Args:
            task: The original task
            result: The current result

        Returns:
            Dictionary containing progress evaluation (action, feedback)
        """
        logger.info("Evaluating progress...")
        try:
            prediction = self.progress_evaluator(task=task, result=result)

            return {
                "action": getattr(prediction, "action", "complete"),
                "feedback": getattr(prediction, "feedback", ""),
                "reasoning": getattr(prediction, "reasoning", ""),
            }
        except Exception as e:
            logger.error(f"Progress evaluation failed: {e}")
            return {
                "action": "complete",
                "feedback": "Evaluation failed",
                "reasoning": str(e),
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

        try:
            prediction = self.tool_planner(task=task, available_tools=team_str)

            return {
                "tool_plan": getattr(prediction, "tool_plan", []),
                "reasoning": getattr(prediction, "reasoning", ""),
            }
        except Exception as e:
            logger.error(f"Tool planning failed: {e}")
            return {
                "tool_plan": [],
                "reasoning": str(e),
            }

    def get_execution_summary(self) -> dict[str, Any]:
        """Return a summary of the execution history."""
        return {
            "history_count": len(self._execution_history),
            # Add more summary stats if needed
        }
