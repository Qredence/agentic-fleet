"""DSPy assertions for validating routing decisions."""

import logging
from typing import TYPE_CHECKING

import dspy

from agentic_fleet.utils.models import ExecutionMode, RoutingDecision

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Mock for type checking if dspy stubs are missing Suggest
    def Suggest(condition: bool, message: str) -> None:  # noqa: N802, D103
        pass
else:
    Suggest = getattr(dspy, "Suggest", None)
    if Suggest is None:
        logger.debug(
            "dspy.Suggest is not available; runtime assertions will be skipped. "
            "Constraints should be learned via GEPA optimization instead."
        )

        # Fallback or dummy if not found at runtime
        def Suggest(condition: bool, message: str) -> None:  # noqa: N802, D103
            pass


def validate_routing_decision(decision: RoutingDecision, task: str) -> None:
    """
    Apply DSPy assertions to validate and refine routing decisions.

    Args:
        decision: The routing decision to validate.
        task: The original task description.
    """
    task_lower = task.lower()

    # Constraint 1: Research tasks need search tools
    if any(kw in task_lower for kw in ["research", "find", "search", "latest", "current"]):
        Suggest(
            "tavilysearchtool" in [t.lower() for t in decision.tool_requirements],
            "Research tasks require the TavilySearchTool to access external information.",
        )

    # Constraint 2: Calculation tasks need code interpreter
    if any(kw in task_lower for kw in ["calculate", "compute", "math", "analysis"]):
        Suggest(
            "hostedcodeinterpretertool" in [t.lower() for t in decision.tool_requirements],
            "Calculation and analysis tasks require the HostedCodeInterpreterTool.",
        )

    # Constraint 3: Multi-agent tasks cannot be delegated
    if len(decision.assigned_to) > 1:
        Suggest(
            decision.mode != ExecutionMode.DELEGATED,
            "Tasks assigned to multiple agents must use SEQUENTIAL or PARALLEL execution mode, not DELEGATED.",
        )

    # Constraint 4: Single-agent tasks should be delegated (soft suggestion)
    if len(decision.assigned_to) == 1:
        Suggest(
            decision.mode == ExecutionMode.DELEGATED,
            "Single-agent tasks should typically use DELEGATED execution mode for efficiency.",
        )
