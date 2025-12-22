"""GEPA (Generalized Evolutionary Prompt Adaptation) module.

Provides DSPy optimization utilities for AgenticFleet routing decisions.
"""

from __future__ import annotations

from .feedback import (
    DEFAULT_HEURISTICS,
    GEPAHeuristics,
    RoutingDecision,
    RoutingFeedbackMetric,
    jaccard_similarity,
    normalize_agents,
    normalize_mode,
    normalize_tools,
)
from .optimizer import (
    convert_to_dspy_examples,
    dedupe_examples,
    harvest_history_examples,
    load_example_dicts,
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
