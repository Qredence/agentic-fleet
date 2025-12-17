"""Typed tool planning module for tool selection.

This module provides a DSPy module for planning tool usage using typed
Pydantic signatures for structured outputs.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import dspy
except ImportError:  # pragma: no cover
    dspy = None  # type: ignore

from ..signatures import TypedToolPlan

logger = logging.getLogger(__name__)


if dspy:

    class ToolPlanningModule(dspy.Module):
        """DSPy module for tool planning with typed Pydantic outputs.

        This module uses TypedToolPlan signature to generate tool usage plans
        with structured, validated outputs.
        """

        def __init__(self) -> None:
            """Initialize the tool planning module."""
            super().__init__()
            # Prefer TypedPredictor when available, otherwise fall back to Predict.
            # (DSPy releases have renamed/removed TypedPredictor across versions.)
            predictor_factory = getattr(dspy, "TypedPredictor", None) or getattr(
                dspy, "Predict", None
            )
            if predictor_factory is None:  # pragma: no cover
                raise RuntimeError(
                    "DSPy predictor API not found (expected TypedPredictor or Predict)"
                )
            self.predictor: Any = predictor_factory(TypedToolPlan)

        def forward(
            self,
            task: str,
            available_tools: str,
            context: str = "",
        ) -> dspy.Prediction:  # type: ignore[name-defined]
            """Generate a tool usage plan for a task.

            Args:
                task: Task description requiring tools
                available_tools: Description of available tools
                context: Optional execution context

            Returns:
                DSPy prediction with tool plan
            """
            return self.predictor(
                task=task,
                available_tools=available_tools,
                context=context,
            )


# Module-level cache for lazy loading
_MODULE_CACHE: dict[str, Any] = {}


def get_tool_planning_module(compiled_module: Any | None = None) -> Any | None:
    """Get or create a tool planning module.

    Args:
        compiled_module: Optional pre-compiled module to use

    Returns:
        ToolPlanningModule instance or None if DSPy unavailable
    """
    if not dspy:
        return None

    # If a compiled module is provided, use it directly
    if compiled_module is not None:
        _MODULE_CACHE["tool_planning"] = compiled_module
        return compiled_module

    # Check cache
    if "tool_planning" in _MODULE_CACHE:
        return _MODULE_CACHE["tool_planning"]

    # Create fresh module (for training/compilation)
    module = ToolPlanningModule()
    _MODULE_CACHE["tool_planning"] = module
    return module


def clear_tool_planning_cache() -> None:
    """Clear the tool planning module cache."""
    _MODULE_CACHE.pop("tool_planning", None)


__all__ = [
    "ToolPlanningModule",
    "clear_tool_planning_cache",
    "get_tool_planning_module",
]
