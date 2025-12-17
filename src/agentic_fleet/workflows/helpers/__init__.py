"""Helper functions for routing, quality assessment, and workflow utilities.

This package provides helpers split into focused modules:
- fast_path: Fast-path detection for simple tasks
- execution: Result synthesis, artifact extraction, work estimation
- routing: Routing decision normalization, edge case detection, subtask preparation
- quality: Quality assessment, judge prompting, result refinement

Public API is maintained via re-exports for backward compatibility.
"""

from __future__ import annotations

from .execution import (
    create_openai_client_with_store,
    derive_objectives,
    estimate_remaining_work,
    extract_artifacts,
    synthesize_results,
)
from .fast_path import FastPathDetector, is_simple_task
from .quality import (
    build_refinement_task,
    call_judge_with_reasoning,
    get_quality_criteria,
    parse_judge_response,
    refine_results,
)
from .routing import (
    detect_routing_edge_cases,
    normalize_routing_decision,
    prepare_subtasks,
)

__all__ = [
    # Fast path
    "FastPathDetector",
    # Quality helpers
    "build_refinement_task",
    "call_judge_with_reasoning",
    # Execution utilities
    "create_openai_client_with_store",
    "derive_objectives",
    # Routing helpers
    "detect_routing_edge_cases",
    "estimate_remaining_work",
    "extract_artifacts",
    "get_quality_criteria",
    "is_simple_task",
    "normalize_routing_decision",
    "parse_judge_response",
    "prepare_subtasks",
    "refine_results",
    "synthesize_results",
]
