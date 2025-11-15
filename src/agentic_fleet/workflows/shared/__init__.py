"""
Shared workflow utilities.

This package contains shared utility functions and data models used across
the fleet workflow implementation, organized into dedicated modules for
better modularity and maintainability.
"""

# Re-export phase functions for simplified imports
from .analysis import (
    analysis_result_from_legacy,
    analysis_result_to_legacy,
    run_analysis_phase,
)
from .execution import run_execution_phase
from .progress import (
    progress_report_from_legacy,
    progress_report_to_legacy,
    run_progress_phase,
)
from .quality import (
    quality_report_from_legacy,
    quality_report_to_legacy,
    run_judge_phase,
    run_quality_phase,
)
from .routing import (
    routing_plan_to_legacy,
    run_routing_phase,
)

__all__ = [
    "analysis_result_from_legacy",
    "analysis_result_to_legacy",
    "progress_report_from_legacy",
    "progress_report_to_legacy",
    "quality_report_from_legacy",
    "quality_report_to_legacy",
    "routing_plan_to_legacy",
    "run_analysis_phase",
    "run_execution_phase",
    "run_judge_phase",
    "run_progress_phase",
    "run_quality_phase",
    "run_routing_phase",
]
