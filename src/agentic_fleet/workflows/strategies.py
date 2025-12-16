"""Execution strategies for the workflow.

This module is a thin facade that re-exports strategy implementations from
the strategies/ subpackage. Import paths remain stable for downstream code.
"""

from __future__ import annotations

from .strategies import (  # type: ignore[import-not-found]
    DelegatedExecutionStrategy,
    DiscussionExecutionStrategy,
    ExecutionPhaseError,
    ParallelExecutionStrategy,
    SequentialExecutionStrategy,
    _extract_tool_usage,
    execute_delegated,
    execute_delegated_streaming,
    execute_discussion_streaming,
    execute_parallel,
    execute_parallel_streaming,
    execute_sequential,
    execute_sequential_streaming,
    execute_sequential_with_handoffs,
    format_handoff_input,
    run_execution_phase,
    run_execution_phase_streaming,
)

__all__ = [
    "DelegatedExecutionStrategy",
    "DiscussionExecutionStrategy",
    "ExecutionPhaseError",
    "ParallelExecutionStrategy",
    "SequentialExecutionStrategy",
    "_extract_tool_usage",
    "execute_delegated",
    "execute_delegated_streaming",
    "execute_discussion_streaming",
    "execute_parallel",
    "execute_parallel_streaming",
    "execute_sequential",
    "execute_sequential_streaming",
    "execute_sequential_with_handoffs",
    "format_handoff_input",
    "run_execution_phase",
    "run_execution_phase_streaming",
]
