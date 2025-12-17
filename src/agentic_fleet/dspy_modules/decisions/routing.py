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
            # Prefer TypedPredictor when available, otherwise fall back to Predict.
            # (DSPy releases have renamed/removed TypedPredictor across versions.)
            predictor_factory = getattr(dspy, "TypedPredictor", None) or getattr(
                dspy, "Predict", None
            )
            if predictor_factory is None:  # pragma: no cover
                raise RuntimeError(
                    "DSPy predictor API not found (expected TypedPredictor or Predict)"
                )
            self.predictor: Any = predictor_factory(TypedEnhancedRouting)

        def forward(self, task: str, **kwargs: Any) -> dspy.Prediction:  # type: ignore[name-defined]
            """Route a task to appropriate agents.

            This module is used in two contexts:

            1) Runtime "enhanced routing" (AgenticFleet default):
               Uses the TypedEnhancedRouting signature fields:
               - team_capabilities
               - available_tools
               - current_context
               - handoff_history
               - workflow_state

            2) Legacy/test callers that pass older field names:
               - team (alias for team_capabilities)
               - context (alias for current_context)
               - current_date (ignored for enhanced routing)

            We accept both shapes and map them to the typed signature.
            """

            team_capabilities = str(kwargs.get("team_capabilities") or kwargs.get("team") or "")
            available_tools = str(kwargs.get("available_tools") or "")
            current_context = str(kwargs.get("current_context") or kwargs.get("context") or "")
            handoff_history = str(kwargs.get("handoff_history") or "")
            workflow_state = str(kwargs.get("workflow_state") or "Active")

            return self.predictor(
                task=task,
                team_capabilities=team_capabilities,
                available_tools=available_tools,
                current_context=current_context,
                handoff_history=handoff_history,
                workflow_state=workflow_state,
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
    _MODULE_CACHE.pop("routing", None)


__all__ = [
    "RoutingDecisionModule",
    "clear_routing_cache",
    "get_routing_module",
]
