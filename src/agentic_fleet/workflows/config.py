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
    parallel_threshold: int = 3
    dspy_model: str = "gpt-5-mini"
    compile_dspy: bool = True
    refinement_threshold: float = 8.0
    enable_refinement: bool = True
    enable_completion_storage: bool = False
    agent_models: dict[str, str] | None = None
    agent_temperatures: dict[str, float] | None = None
    history_format: str = "jsonl"
    examples_path: str = "data/supervisor_examples.json"
    dspy_optimizer: str = "bootstrap"
    gepa_options: dict[str, Any] | None = None
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
