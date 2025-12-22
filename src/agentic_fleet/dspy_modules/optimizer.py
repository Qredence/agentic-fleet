"""
GEPA Optimizer Facade.

This module provides a convenient entry point for the GEPA optimizer,
re-exporting the core functionality from `dspy_modules.gepa.optimizer`.

It simplifies the import path for consumers (services, API routes) who need
to access the optimization loop.
"""

from agentic_fleet.dspy_modules.gepa.optimizer import (
    convert_to_dspy_examples,
    dedupe_examples,
    harvest_history_examples,
    load_example_dicts,
    optimize_with_gepa,
    prepare_gepa_datasets,
)

__all__ = [
    "convert_to_dspy_examples",
    "dedupe_examples",
    "harvest_history_examples",
    "load_example_dicts",
    "optimize_with_gepa",
    "prepare_gepa_datasets",
]
