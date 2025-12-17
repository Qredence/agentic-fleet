"""Deprecated legacy executors.

This module is intentionally kept extremely small.

Historically it contained optional/legacy workflow executors (e.g. judge/refine).
Those are not part of the default workflow graph anymore.

If you need a DSPy-backed executor, import `DSPyExecutor` from:
- `agentic_fleet.workflows.executors` (preferred stable facade), or
- `agentic_fleet.workflows.executors_dspy`.

`JudgeRefineExecutor` was removed in Plan #4; this module now provides a stub
that fails fast with a helpful error if referenced by old custom configs.
"""

from __future__ import annotations

from typing import Any

from agent_framework._workflows import Executor

from .dspy_executor import DSPyExecutor


class JudgeRefineExecutor(Executor):
    """Removed executor kept only as a compatibility stub."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Accept arbitrary parameters to stay compatible with older custom workflow graphs.
        _ = (args, kwargs)
        raise RuntimeError(
            "JudgeRefineExecutor was removed from AgenticFleet (Plan #4). "
            "Update your custom workflow graph to terminate at QualityExecutor or "
            "remove judge/refine edges entirely."
        )


__all__ = ["DSPyExecutor", "JudgeRefineExecutor"]
