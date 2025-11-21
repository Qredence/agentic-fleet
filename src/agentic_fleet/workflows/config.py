"""Workflow configuration dataclass and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkflowConfig:
    """Configuration for workflow execution."""

    max_rounds: int = 15
    max_stalls: int = 3
    max_resets: int = 2
    enable_streaming: bool = True
    # Pipeline profile:
    # - "full": full multi-stage pipeline with analysis/routing/progress/quality/judge
    # - "light": latency-optimized path for simple tasks
    pipeline_profile: str = "full"
    # Heuristic threshold for simple-task detection (word count)
    simple_task_max_words: int = 40
    parallel_threshold: int = 3
    dspy_model: str = "gpt-5-mini"
    dspy_temperature: float = 1.0
    dspy_max_tokens: int = 16000
    compile_dspy: bool = True
    refinement_threshold: float = 8.0
    enable_refinement: bool = True
    # Whether to call DSPy for progress/quality assessment.
    # These can be disabled in "light" profile to reduce LM calls.
    enable_progress_eval: bool = True
    enable_quality_eval: bool = True
    enable_completion_storage: bool = False
    agent_models: dict[str, str] | None = None
    agent_temperatures: dict[str, float] | None = None
    agent_strategies: dict[str, str] | None = None
    history_format: str = "jsonl"
    examples_path: str = "data/supervisor_examples.json"
    dspy_optimizer: str = "bootstrap"
    gepa_options: dict[str, Any] | None = None
    allow_gepa_optimization: bool = False  # Default to False for safety
    enable_handoffs: bool = True
    max_task_length: int = 10000
    quality_threshold: float = 8.0
    dspy_retry_attempts: int = 3
    dspy_retry_backoff_seconds: float = 1.0
    analysis_cache_ttl_seconds: int = 3600
    judge_threshold: float = 7.0
    max_refinement_rounds: int = 2
    enable_judge: bool = True
    judge_model: str | None = None
    judge_reasoning_effort: str = "medium"

    # ------------------------------------------------------------------
    # Backward-compatibility: some tests expect a ``config`` attribute
    # exposing dict-like access to underlying settings.
    # ------------------------------------------------------------------
    @property
    def config(self) -> dict[str, Any]:
        """Return a dict-like view of configuration fields."""
        return self.__dict__
