"""Typed quality assessment module for answer scoring.

This module provides a DSPy module for assessing answer quality using typed
Pydantic signatures for structured outputs.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import dspy
except ImportError:  # pragma: no cover
    dspy = None  # type: ignore

from ..signatures import TypedQualityAssessment

logger = logging.getLogger(__name__)


if dspy:

    class QualityDecisionModule(dspy.Module):
        """DSPy module for quality assessment with typed Pydantic outputs.

        This module uses TypedQualityAssessment signature to evaluate answer
        quality with structured, validated outputs.
        """

        def __init__(self) -> None:
            """Initialize the quality assessment module."""
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
            self.predictor: Any = predictor_factory(TypedQualityAssessment)

        def forward(
            self,
            task: str,
            result: str,
        ) -> dspy.Prediction:  # type: ignore[name-defined]
            """Assess the quality of a task result.

            Args:
                task: Original task description
                result: Result produced by the agent

            Returns:
                DSPy prediction with quality assessment
            """
            return self.predictor(
                task=task,
                result=result,
            )


# Module-level cache for lazy loading
_MODULE_CACHE: dict[str, Any] = {}


def get_quality_module(compiled_module: Any | None = None) -> Any | None:
    """Get or create a quality assessment module.

    Args:
        compiled_module: Optional pre-compiled module to use

    Returns:
        QualityDecisionModule instance or None if DSPy unavailable
    """
    if not dspy:
        return None

    # If a compiled module is provided, use it directly
    if compiled_module is not None:
        _MODULE_CACHE["quality"] = compiled_module
        return compiled_module

    # Check cache
    if "quality" in _MODULE_CACHE:
        return _MODULE_CACHE["quality"]

    # Create fresh module (for training/compilation)
    module = QualityDecisionModule()
    _MODULE_CACHE["quality"] = module
    return module


def clear_quality_cache() -> None:
    """Clear the quality module cache."""
    _MODULE_CACHE.pop("quality", None)


__all__ = [
    "QualityDecisionModule",
    "clear_quality_cache",
    "get_quality_module",
]
