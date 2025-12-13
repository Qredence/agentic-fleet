"""Typed routing decision module for task assignment.

This module provides a DSPy module for routing tasks to appropriate agents
using typed Pydantic signatures for structured outputs.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import dspy
except ImportError:  # pragma: no cover
    dspy = None  # type: ignore

from ..signatures import TypedEnhancedRouting
from ..typed_models import RoutingDecisionOutput

logger = logging.getLogger(__name__)


if dspy:

    class RoutingDecisionModule(dspy.Module):
        """DSPy module for routing decisions with typed Pydantic outputs.

        This module uses TypedEnhancedRouting signature to route tasks to
        appropriate agents with structured, validated outputs.
        """

        def __init__(self) -> None:
            """Initialize the routing decision module."""
            super().__init__()
            # Use TypedPredictor for structured Pydantic outputs
            self.predictor: Any = dspy.TypedPredictor(TypedEnhancedRouting)

        def forward(
            self,
            task: str,
            team: str,
            context: str = "",
            current_date: str = "",
            available_tools: str = "",
        ) -> dspy.Prediction:  # type: ignore[name-defined]
            """Route a task to appropriate agents.

            Args:
                task: Task description to route
                team: Description of available agents
                context: Optional execution context
                current_date: Current date for time-sensitive decisions
                available_tools: Available tools for the task

            Returns:
                DSPy prediction with routing decision
            """
            return self.predictor(
                task=task,
                team=team,
                context=context,
                current_date=current_date,
                available_tools=available_tools,
            )


# Module-level cache for lazy loading
_MODULE_CACHE: dict[str, Any] = {}


def get_routing_module(compiled_module: Any | None = None) -> Any | None:
    """Get or create a routing decision module.

    Args:
        compiled_module: Optional pre-compiled module to use

    Returns:
        RoutingDecisionModule instance or None if DSPy unavailable
    """
    if not dspy:
        return None

    # If a compiled module is provided, use it directly
    if compiled_module is not None:
        _MODULE_CACHE["routing"] = compiled_module
        return compiled_module

    # Check cache
    if "routing" in _MODULE_CACHE:
        return _MODULE_CACHE["routing"]

    # Create fresh module (for training/compilation)
    module = RoutingDecisionModule()
    _MODULE_CACHE["routing"] = module
    return module


def clear_routing_cache() -> None:
    """Clear the routing module cache."""
    if "routing" in _MODULE_CACHE:
        del _MODULE_CACHE["routing"]


__all__ = [
    "RoutingDecisionModule",
    "get_routing_module",
    "clear_routing_cache",
]
