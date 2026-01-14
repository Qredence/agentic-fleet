"""Optimization module for AgenticFleet DSPy integration.

Provides GEPA (Generalized Evolutionary Prompt Adaptation) optimization utilities.
"""

from __future__ import annotations

from .gepa import (
    DEFAULT_HEURISTICS,
    GEPAHeuristics,
    RoutingDecision,
    RoutingFeedbackMetric,
    convert_to_dspy_examples,
    dedupe_examples,
    harvest_history_examples,
    jaccard_similarity,
    load_example_dicts,
    normalize_agents,
    normalize_mode,
    normalize_tools,
    optimize_with_gepa,
    prepare_gepa_datasets,
)
from .self_improvement import SelfImprovementEngine

__all__ = [
    "DEFAULT_HEURISTICS",
    "GEPAHeuristics",
    "RoutingDecision",
    "RoutingFeedbackMetric",
    "SelfImprovementEngine",
    "convert_to_dspy_examples",
    "dedupe_examples",
    "harvest_history_examples",
    "jaccard_similarity",
    "load_example_dicts",
    "normalize_agents",
    "normalize_mode",
    "normalize_tools",
    "optimize_with_gepa",
    "prepare_gepa_datasets",
]
