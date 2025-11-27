"""
Configuration schema validation using Pydantic.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class DSPyOptimizationConfig(BaseModel):
    """DSPy optimization configuration."""

    enabled: bool = True
    examples_path: str = "data/supervisor_examples.json"
    metric_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_bootstrapped_demos: int = Field(default=4, ge=1, le=20)
    use_gepa: bool = False
    gepa_auto: Literal["light", "medium", "heavy"] = "light"
    gepa_max_full_evals: int = Field(default=50, ge=1)
    gepa_max_metric_calls: int = Field(default=150, ge=1)
    gepa_reflection_model: str | None = None
    gepa_log_dir: str = "logs/gepa"
    gepa_perfect_score: float = Field(default=1.0, ge=0.0, le=10.0)
    gepa_use_history_examples: bool = False
    gepa_history_min_quality: float = Field(default=8.0, ge=0.0, le=10.0)
    gepa_history_limit: int = Field(default=200, ge=1)
    gepa_val_split: float = Field(default=0.2, ge=0.0, le=0.5)
    gepa_seed: int = Field(default=13, ge=0)


class DSPyConfig(BaseModel):
    """DSPy configuration."""

    model: str = "gpt-5-mini"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=1, le=32000)
    # When true, raise an error if no compiled DSPy artifact is found.
    # Recommended for production environments to prevent degraded performance.
    # Run 'agentic-fleet optimize' to generate compiled artifacts before enabling.
    require_compiled: bool = False
    optimization: DSPyOptimizationConfig = DSPyOptimizationConfig()


class SupervisorConfig(BaseModel):
    """Supervisor configuration."""

    max_rounds: int = Field(default=15, ge=1, le=100)
    max_stalls: int = Field(default=3, ge=1, le=20)
    max_resets: int = Field(default=2, ge=0, le=10)
    enable_streaming: bool = True
    # Pipeline profile: "full" = full multi-stage pipeline,
    # "light" = latency-optimized path for simple tasks.
    pipeline_profile: Literal["full", "light"] = "full"
    # Heuristic threshold (word count) for classifying simple tasks.
    simple_task_max_words: int = Field(default=40, ge=1, le=2000)


class ExecutionConfig(BaseModel):
    """Execution configuration."""

    parallel_threshold: int = Field(default=3, ge=1)
    timeout_seconds: int = Field(default=300, ge=1)
    retry_attempts: int = Field(default=2, ge=0)


class QualityConfig(BaseModel):
    """Quality assessment configuration."""

    refinement_threshold: float = Field(default=8.0, ge=0.0, le=10.0)
    enable_refinement: bool = True
    # Whether to invoke DSPy for progress / quality evaluation stages.
    # These can be disabled in light/fast paths to reduce LM calls.
    enable_progress_eval: bool = True
    enable_quality_eval: bool = True
    judge_threshold: float = Field(default=7.0, ge=0.0, le=10.0)
    enable_judge: bool = True
    max_refinement_rounds: int = Field(default=2, ge=1, le=5)
    judge_model: str | None = None
    judge_reasoning_effort: Literal["minimal", "medium", "maximal"] = "medium"


class HandoffConfig(BaseModel):
    """Handoff workflow configuration."""

    enabled: bool = True


class WorkflowConfig(BaseModel):
    """Workflow configuration."""

    supervisor: SupervisorConfig = SupervisorConfig()
    execution: ExecutionConfig = ExecutionConfig()
    quality: QualityConfig = QualityConfig()
    handoffs: HandoffConfig = HandoffConfig()


class AgentConfig(BaseModel):
    """Agent configuration."""

    model: str = "gpt-5-mini"
    tools: list[str] = Field(default_factory=list)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    enable_dspy: bool = True
    cache_ttl: int = Field(default=300, ge=0)
    timeout: int = Field(default=30, ge=1)
    strategy: str | None = None
    instructions: str | None = None

    model_config = {"extra": "allow"}


class AgentsConfig(BaseModel):
    """Agents configuration."""

    researcher: AgentConfig = AgentConfig()
    analyst: AgentConfig = AgentConfig()
    writer: AgentConfig = AgentConfig()
    reviewer: AgentConfig = AgentConfig()

    model_config = {"extra": "allow"}


class ToolsConfig(BaseModel):
    """Tools configuration."""

    enable_tool_aware_routing: bool = True
    pre_analysis_tool_usage: bool = True
    tool_registry_cache: bool = True
    tool_usage_tracking: bool = True


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/workflow.log"
    save_history: bool = True
    history_file: str = "logs/execution_history.jsonl"
    verbose: bool = True

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {v}. Must be one of {valid_levels}")
        return v.upper()


class OpenAIConfig(BaseModel):
    """OpenAI configuration."""

    enable_completion_storage: bool = False


class TracingConfig(BaseModel):
    """Tracing / observability configuration."""

    enabled: bool = False
    otlp_endpoint: str = "http://localhost:4317"
    capture_sensitive: bool = True


class EvaluationConfig(BaseModel):
    """Evaluation framework configuration."""

    enabled: bool = False
    dataset_path: str = "data/evaluation_tasks.jsonl"
    output_dir: str = "logs/evaluation"
    metrics: list[str] = Field(
        default_factory=lambda: [
            "quality_score",
            "keyword_success",
            "latency_seconds",
            "routing_efficiency",
            "refinement_triggered",
        ]
    )
    max_tasks: int = Field(default=0, ge=0)  # 0 = no limit
    stop_on_failure: bool = False


class WorkflowConfigSchema(BaseModel):
    """Complete workflow configuration schema."""

    dspy: DSPyConfig = DSPyConfig()
    workflow: WorkflowConfig = WorkflowConfig()
    agents: AgentsConfig = AgentsConfig()
    tools: ToolsConfig = ToolsConfig()
    logging: LoggingConfig = LoggingConfig()
    openai: OpenAIConfig = OpenAIConfig()
    tracing: TracingConfig = TracingConfig()
    evaluation: EvaluationConfig = EvaluationConfig()

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> WorkflowConfigSchema:
        """Create schema from dictionary, filling in defaults for missing keys."""
        return cls.model_validate(config_dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert schema to dictionary."""
        return self.model_dump(mode="json")


def validate_config(config_dict: dict[str, Any]) -> WorkflowConfigSchema:
    """
    Validate configuration dictionary.

    Args:
        config_dict: Configuration dictionary to validate

    Returns:
        Validated WorkflowConfigSchema instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    try:
        return WorkflowConfigSchema.from_dict(config_dict)
    except Exception as e:
        from ..workflows.exceptions import ConfigurationError

        raise ConfigurationError(f"Invalid configuration: {e}") from e
