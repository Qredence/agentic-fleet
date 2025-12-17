"""Workflow configuration dataclass and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic_fleet.utils.cfg import DEFAULT_GEPA_LOG_DIR, DEFAULT_HISTORY_PATH, get_agent_model


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
    # ------------------------------------------------------------------
    # Conversation context injection
    # ------------------------------------------------------------------
    # For short follow-up inputs (quick replies), include a small window of
    # recent conversation messages when performing analysis/routing.
    conversation_context_max_messages: int = 8
    conversation_context_max_chars: int = 4000
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
    require_compiled: bool = False

    # ------------------------------------------------------------------
    # DSPy 3.x TypedPredictor Settings
    # ------------------------------------------------------------------
    # Enable Pydantic-based typed signatures for structured outputs.
    # This improves output parsing reliability and validation.
    use_typed_signatures: bool = True
    # Cache routing decisions to avoid redundant LLM calls
    enable_routing_cache: bool = True
    # TTL for routing cache entries (in seconds)
    routing_cache_ttl_seconds: int = 300

    # ------------------------------------------------------------------
    # Backward-compatibility: some tests expect a ``config`` attribute
    # exposing dict-like access to underlying settings.
    # ------------------------------------------------------------------
    @property
    def config(self) -> dict[str, Any]:
        """Return a dict-like view of configuration fields."""
        return self.__dict__


def build_workflow_config_from_yaml(
    yaml_config: dict[str, Any],
    *,
    compile_dspy: bool = False,
    max_rounds: int | None = None,
    model: str | None = None,
    enable_handoffs: bool | None = None,
    pipeline_profile: str | None = None,
    allow_gepa: bool = False,
) -> WorkflowConfig:
    """Build a WorkflowConfig from YAML configuration dictionary.

    This function extracts workflow configuration from the YAML config dict
    and constructs a WorkflowConfig dataclass instance. Used by both CLI runner
    and API services to ensure consistent configuration across entry points.

    Args:
        yaml_config: YAML configuration dictionary (from load_config())
        compile_dspy: Whether to enable DSPy compilation (default: False for API)
        max_rounds: Override max_rounds (defaults to YAML value)
        model: Override DSPy model (defaults to YAML value)
        enable_handoffs: Override handoffs setting (defaults to YAML value)
        pipeline_profile: Override pipeline profile (defaults to YAML value)
        allow_gepa: Whether to allow GEPA optimization (default: False)

    Returns:
        WorkflowConfig instance populated from YAML with any overrides applied
    """
    opt_cfg = yaml_config.get("dspy", {}).get("optimization", {})
    examples_path = opt_cfg.get("examples_path", "data/supervisor_examples.json")
    use_gepa = opt_cfg.get("use_gepa", False)

    # GEPA exclusivity resolution
    auto_choice = opt_cfg.get("gepa_auto")
    full_evals_choice = opt_cfg.get("gepa_max_full_evals")
    metric_calls_choice = opt_cfg.get("gepa_max_metric_calls")

    if auto_choice:
        full_evals_choice = None
        metric_calls_choice = None
    elif full_evals_choice is not None:
        auto_choice = None
        metric_calls_choice = None
    elif metric_calls_choice is not None:
        auto_choice = None
        full_evals_choice = None

    # Determine effective model
    effective_model = model or yaml_config.get("dspy", {}).get("model", "gpt-5-mini")

    # Build optimization options
    reflection_model_value = (
        opt_cfg.get("gepa_reflection_model") or effective_model if use_gepa else None
    )

    if auto_choice is not None:
        final_auto = auto_choice
    elif full_evals_choice is not None or metric_calls_choice is not None:
        final_auto = None
    else:
        final_auto = "light"

    optimization_options: dict[str, Any] = {
        "auto": final_auto,
        "max_full_evals": full_evals_choice,
        "max_metric_calls": metric_calls_choice,
        "reflection_model": reflection_model_value,
        "log_dir": opt_cfg.get("gepa_log_dir", DEFAULT_GEPA_LOG_DIR),
        "perfect_score": opt_cfg.get("gepa_perfect_score", 1.0),
        "use_history_examples": opt_cfg.get("gepa_use_history_examples", False),
        "history_min_quality": opt_cfg.get("gepa_history_min_quality", 8.0),
        "history_limit": opt_cfg.get("gepa_history_limit", 200),
        "val_split": opt_cfg.get("gepa_val_split", 0.2),
        "seed": opt_cfg.get("gepa_seed", 13),
        "max_bootstrapped_demos": opt_cfg.get("max_bootstrapped_demos", 4),
    }
    if optimization_options.get("reflection_model") is None:
        optimization_options.pop("reflection_model", None)

    # Build WorkflowConfig
    history_file = yaml_config.get("logging", {}).get("history_file", DEFAULT_HISTORY_PATH)
    history_format = "jsonl" if str(history_file).endswith(".jsonl") else "json"

    handoffs_cfg = (
        yaml_config.get("workflow", {}).get("handoffs", {})
        if isinstance(yaml_config.get("workflow"), dict)
        else {}
    )
    handoffs_enabled = (
        enable_handoffs if enable_handoffs is not None else handoffs_cfg.get("enabled", True)
    )

    # Determine pipeline profile (full vs light)
    supervisor_cfg = (
        yaml_config.get("workflow", {}).get("supervisor", {})
        if isinstance(yaml_config.get("workflow"), dict)
        else {}
    )
    effective_profile = (
        pipeline_profile
        if pipeline_profile is not None
        else supervisor_cfg.get("pipeline_profile", "full")
    )
    simple_task_max_words = supervisor_cfg.get("simple_task_max_words", 40)
    conversation_context_max_messages = supervisor_cfg.get("conversation_context_max_messages", 8)
    conversation_context_max_chars = supervisor_cfg.get("conversation_context_max_chars", 4000)

    quality_cfg = (
        yaml_config.get("workflow", {}).get("quality", {})
        if isinstance(yaml_config.get("workflow"), dict)
        else {}
    )

    return WorkflowConfig(
        max_rounds=max_rounds or supervisor_cfg.get("max_rounds", 15),
        max_stalls=supervisor_cfg.get("max_stalls", 3),
        max_resets=supervisor_cfg.get("max_resets", 2),
        enable_streaming=supervisor_cfg.get("enable_streaming", True),
        pipeline_profile=effective_profile,
        simple_task_max_words=simple_task_max_words,
        conversation_context_max_messages=int(conversation_context_max_messages),
        conversation_context_max_chars=int(conversation_context_max_chars),
        parallel_threshold=yaml_config.get("workflow", {})
        .get("execution", {})
        .get("parallel_threshold", 3),
        dspy_model=effective_model,
        dspy_temperature=yaml_config.get("dspy", {}).get("temperature", 0.7),
        dspy_max_tokens=yaml_config.get("dspy", {}).get("max_tokens", 2000),
        compile_dspy=compile_dspy,
        require_compiled=yaml_config.get("dspy", {}).get("require_compiled", False),
        refinement_threshold=quality_cfg.get("refinement_threshold", 8.0),
        enable_refinement=quality_cfg.get("enable_refinement", True),
        enable_progress_eval=quality_cfg.get("enable_progress_eval", True),
        enable_quality_eval=quality_cfg.get("enable_quality_eval", True),
        judge_threshold=quality_cfg.get("judge_threshold", 7.0),
        enable_judge=quality_cfg.get("enable_judge", True),
        max_refinement_rounds=quality_cfg.get("max_refinement_rounds", 2),
        judge_model=quality_cfg.get("judge_model"),
        judge_reasoning_effort=quality_cfg.get("judge_reasoning_effort", "medium"),
        enable_completion_storage=yaml_config.get("openai", {}).get(
            "enable_completion_storage", False
        ),
        agent_models={
            name.lower(): get_agent_model(yaml_config, name, effective_model)
            for name in yaml_config.get("agents", {})
        },
        agent_temperatures={
            name.lower(): yaml_config.get("agents", {}).get(name.lower(), {}).get("temperature")
            for name in yaml_config.get("agents", {})
        },
        agent_strategies={
            name.lower(): yaml_config.get("agents", {}).get(name.lower(), {}).get("strategy")
            for name in yaml_config.get("agents", {})
        },
        history_format=history_format,
        examples_path=examples_path,
        dspy_optimizer="gepa" if use_gepa else "bootstrap",
        gepa_options=optimization_options,
        enable_handoffs=handoffs_enabled,
        allow_gepa_optimization=allow_gepa,
        use_typed_signatures=yaml_config.get("dspy", {}).get("use_typed_signatures", True),
        enable_routing_cache=yaml_config.get("dspy", {}).get("enable_routing_cache", True),
        routing_cache_ttl_seconds=yaml_config.get("dspy", {}).get("routing_cache_ttl_seconds", 300),
    )
