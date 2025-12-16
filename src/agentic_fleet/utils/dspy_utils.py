"""
DSPy-focused utility surface combining compilation, LM management, GEPA optimization,
and self-improvement helpers.

Existing modules remain intact; this file provides a convenience import surface.
"""

from __future__ import annotations

from ..dspy_modules.lifecycle import (
    configure_dspy_settings,
    get_dspy_lm,
    get_reflection_lm,
    reset_dspy_manager,
)
from .compiler import compile_reasoner
from .gepa_optimizer import (
    convert_to_dspy_examples,
    harvest_history_examples,
    optimize_with_gepa,
    prepare_gepa_datasets,
)
from .self_improvement import SelfImprovementEngine

__all__ = [
    "SelfImprovementEngine",
    "compile_reasoner",
    "configure_dspy_settings",
    "convert_to_dspy_examples",
    "get_dspy_lm",
    "get_reflection_lm",
    "harvest_history_examples",
    "optimize_with_gepa",
    "prepare_gepa_datasets",
    "reset_dspy_manager",
]
