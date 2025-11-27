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
    parallel_threshold: int = 2
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
    # GEPA optimization (e.g., Gradient-based Efficient Prompt Adaptation) is disabled by default.
    # This feature is experimental and may introduce instability, unpredictable model behaviour,
    # or potential security risks (such as leaking sensitive data or bypassing safety checks).
    # Enable only in trusted environments, for advanced users, or after thorough testing.
    # Recommended: leave disabled unless you fully understand the implications.
    allow_gepa_optimization: bool = False
    enable_handoffs: bool = True
    max_task_length: int = 10000
    quality_threshold: float = 8.0
    dspy_retry_attempts: int = 3
    dspy_retry_backoff_seconds: float = 1.0
    # Maximum number of DSPy backtracks/retries for assertion failures.
    # Setting this higher improves robustness but increases latency.
    dspy_max_backtracks: int = 2
    analysis_cache_ttl_seconds: int = 3600
    judge_threshold: float = 6.5
    max_refinement_rounds: int = 1
    enable_judge: bool = True
    judge_model: str | None = None
    judge_reasoning_effort: str = "low"

    # ------------------------------------------------------------------
    # DSPy Compilation Settings
    # ------------------------------------------------------------------
    # When True, raise an error if no compiled DSPy artifact is found.
    # This is recommended for production environments to avoid degraded
    # performance from zero-shot fallback. Run 'agentic-fleet optimize'
    # to generate compiled artifacts before enabling this flag.
    require_compiled_dspy: bool = False

    # ------------------------------------------------------------------
    # Backward-compatibility: some tests expect a ``config`` attribute
    # exposing dict-like access to underlying settings.
    # ------------------------------------------------------------------
    @property
    def config(self) -> dict[str, Any]:
        """Return a dict-like view of configuration fields."""
        return self.__dict__
