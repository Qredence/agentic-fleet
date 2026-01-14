"""Pydantic configuration schemas for AgenticFleet.

This module defines all configuration schemas used for validating
workflow_config.yaml and providing type-safe configuration access.

Schemas are organized hierarchically:
- DSPyConfig: DSPy model and optimization settings
- WorkflowConfig: Supervisor, execution, and quality settings
- AgentsConfig: Per-agent model and tool configuration
- WorkflowConfigSchema: Root schema combining all sections
"""

# ruff: noqa: D102

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# LiteLLM Model Validation
# =============================================================================

_LITELLM_ALLOWED_MODELS = {
    "deepinfra/nvidia/Nemotron-3-Nano-30B-A3B",
    "deepinfra/deepseek-ai/DeepSeek-V3.2",
    "deepinfra/deepseek-ai/DeepSeek-R1-0528",
    "gemini/gemini-3-flash-preview",
    "gemini/gemini-3-pro-preview",
    "nvidia_nim/nvidia/nemotron-3-nano-30b-a3b",
}


def _validate_litellm_model(value: str, field_name: str) -> str:
    if not value:
        return value
    if "/" in value and value not in _LITELLM_ALLOWED_MODELS:
        allowed = ", ".join(sorted(_LITELLM_ALLOWED_MODELS))
        raise ValueError(
            f"Unsupported model '{value}' for {field_name}. "
            f"Allowed LiteLLM models: {allowed}. "
            "Update scripts/validate_litellm_models.sh and schema if adding new models."
        )
    return value


# =============================================================================
# DSPy Configuration
# =============================================================================


class DSPyOptimizationConfig(BaseModel):
    """DSPy optimization configuration."""

    enabled: bool = True
    examples_path: str = "src/agentic_fleet/data/supervisor_examples.json"
    metric_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_bootstrapped_demos: int = Field(default=4, ge=1, le=20)
    use_gepa: bool = False
    gepa_auto: Literal["light", "medium", "heavy"] = "light"
    gepa_max_full_evals: int = Field(default=50, ge=1)
    gepa_max_metric_calls: int = Field(default=150, ge=1)
    gepa_reflection_model: str | None = None
    gepa_log_dir: str = ".var/logs/gepa"
    gepa_perfect_score: float = Field(default=1.0, ge=0.0, le=10.0)
    gepa_use_history_examples: bool = False
    gepa_history_min_quality: float = Field(default=8.0, ge=0.0, le=10.0)
    gepa_history_limit: int = Field(default=200, ge=1)
    gepa_val_split: float = Field(default=0.2, ge=0.0, le=0.5)
    gepa_seed: int = Field(default=13, ge=0)

    @field_validator("gepa_reflection_model")
    @classmethod
    def validate_gepa_reflection_model(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_litellm_model(v, "dspy.optimization.gepa_reflection_model")


class DSPyConfig(BaseModel):
    """DSPy configuration."""

    model: str = "gpt-5-mini"
    routing_model: str | None = None  # Optional fast model for routing/analysis
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=1, le=32000)
    compiled_reasoner_path: str = ".var/cache/dspy/compiled_reasoner.json"
    require_compiled: bool = False
    # Routing/cache configuration for DSPy-based supervisors and agents
    enable_routing_cache: bool = True  # Cache routing decisions
    routing_cache_ttl_seconds: int = Field(default=300, ge=0)  # Cache TTL in seconds
    optimization: DSPyOptimizationConfig = DSPyOptimizationConfig()

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        return _validate_litellm_model(v, "dspy.model")

    @field_validator("routing_model")
    @classmethod
    def validate_routing_model(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_litellm_model(v, "dspy.routing_model")


# =============================================================================
# Workflow Configuration
# =============================================================================


class SupervisorConfig(BaseModel):
    """Supervisor configuration."""

    max_rounds: int = Field(default=15, ge=1, le=100)
    max_stalls: int = Field(default=3, ge=1, le=20)
    max_resets: int = Field(default=2, ge=0, le=10)
    enable_streaming: bool = True
    pipeline_profile: Literal["full", "light"] = "full"
    simple_task_max_words: int = Field(default=40, ge=1, le=2000)
    # Include a small recent message window in analysis/routing to resolve
    # short follow-up inputs (e.g., quick replies).
    conversation_context_max_messages: int = Field(default=8, ge=0, le=50)
    conversation_context_max_chars: int = Field(default=4000, ge=0, le=20000)


class ExecutionConfig(BaseModel):
    """Execution configuration."""

    parallel_threshold: int = Field(default=3, ge=1)
    timeout_seconds: int = Field(default=300, ge=1)
    retry_attempts: int = Field(default=2, ge=0)


class QualityConfig(BaseModel):
    """Quality assessment configuration."""

    refinement_threshold: float = Field(default=8.0, ge=0.0, le=10.0)
    enable_refinement: bool = True
    enable_progress_eval: bool = True
    enable_quality_eval: bool = True
    judge_threshold: float = Field(default=7.0, ge=0.0, le=10.0)
    enable_judge: bool = True
    max_refinement_rounds: int = Field(default=2, ge=1, le=5)
    judge_model: str | None = None
    judge_reasoning_effort: Literal["minimal", "medium", "maximal"] = "medium"

    @field_validator("judge_model")
    @classmethod
    def validate_judge_model(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_litellm_model(v, "workflow.quality.judge_model")


class HandoffConfig(BaseModel):
    """Handoff workflow configuration."""

    enabled: bool = True


class WorkflowConfig(BaseModel):
    """Workflow configuration."""

    supervisor: SupervisorConfig = SupervisorConfig()
    execution: ExecutionConfig = ExecutionConfig()
    quality: QualityConfig = QualityConfig()
    handoffs: HandoffConfig = HandoffConfig()


# =============================================================================
# Agent Configuration
# =============================================================================


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

    model_config = ConfigDict(extra="allow")

    @field_validator("model")
    @classmethod
    def validate_agent_model(cls, v: str) -> str:
        return _validate_litellm_model(v, "agents.*.model")


class AgentsConfig(BaseModel):
    """Agents configuration."""

    researcher: AgentConfig = AgentConfig()
    analyst: AgentConfig = AgentConfig()
    writer: AgentConfig = AgentConfig()
    reviewer: AgentConfig = AgentConfig()

    model_config = ConfigDict(extra="allow")


# =============================================================================
# Tools Configuration
# =============================================================================


class ToolsConfig(BaseModel):
    """Tools configuration."""

    enable_tool_aware_routing: bool = True
    pre_analysis_tool_usage: bool = True
    tool_registry_cache: bool = True
    tool_usage_tracking: bool = True


# =============================================================================
# Logging Configuration
# =============================================================================


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = ".var/logs/workflow.log"
    save_history: bool = True
    history_file: str = ".var/logs/execution_history.jsonl"
    verbose: bool = True
    log_reasoning: bool = False

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {v}. Must be one of {valid_levels}")
        return v.upper()


# =============================================================================
# OpenAI Configuration
# =============================================================================


class OpenAIConfig(BaseModel):
    """OpenAI configuration."""

    enable_completion_storage: bool = False


# =============================================================================
# Tracing Configuration
# =============================================================================


class TracingConfig(BaseModel):
    """Tracing / observability configuration.

    This configuration controls OpenTelemetry-based tracing for workflow observability.

    Attributes:
        enabled: Enable/disable tracing. Defaults to False.
        otlp_endpoint: OpenTelemetry collector endpoint. Defaults to http://localhost:4317.
        capture_sensitive: Whether to capture sensitive data (API keys, user inputs, etc.)
            in trace spans. Defaults to False for security.

    Security Note:
        The `capture_sensitive` field defaults to False following the principle of
        secure-by-default. When False, sensitive data such as API keys, user inputs,
        and potentially identifying information will be redacted from trace spans.

        Set to True only in development/debugging scenarios where:
        - You need full request/response visibility for troubleshooting
        - Your tracing backend has appropriate access controls
        - You understand the privacy implications

    Migration Note:
        Users who previously relied on full trace data visibility for debugging
        should explicitly set `capture_sensitive: true` in their configuration
        if they need this behavior. Production environments should keep this False.

    Example:
        In workflow_config.yaml:

        .. code-block:: yaml

            tracing:
              enabled: true
              otlp_endpoint: "http://localhost:4317"
              capture_sensitive: false  # Keep false in production
    """

    enabled: bool = False
    otlp_endpoint: str = "http://localhost:4317"
    capture_sensitive: bool = False


# =============================================================================
# Evaluation Configuration
# =============================================================================


class EvaluationConfig(BaseModel):
    """Evaluation framework configuration."""

    enabled: bool = False
    dataset_path: str = "src/agentic_fleet/data/evaluation_tasks.jsonl"
    output_dir: str = ".var/logs/evaluation"
    metrics: list[str] = Field(
        default_factory=lambda: [
            "quality_score",
            "keyword_success",
            "latency_seconds",
            "routing_efficiency",
            "refinement_triggered",
        ]
    )
    max_tasks: int = Field(default=0, ge=0)
    stop_on_failure: bool = False


# =============================================================================
# Root Configuration Schema
# =============================================================================


class WorkflowConfigSchema(BaseModel):
    """Complete workflow configuration schema.

    This is the root schema that combines all configuration sections.
    It validates the entire workflow_config.yaml structure.
    """

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
        """Create schema from dictionary."""
        return cls.model_validate(config_dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert schema to dictionary."""
        return self.model_dump(mode="json")


# =============================================================================
# Validation Function
# =============================================================================


def validate_config(config_dict: dict[str, Any]) -> WorkflowConfigSchema:
    """Validate configuration dictionary against the schema.

    Args:
        config_dict: Raw configuration dictionary

    Returns:
        Validated WorkflowConfigSchema instance

    Raises:
        ConfigurationError: If validation fails
    """
    try:
        return WorkflowConfigSchema.from_dict(config_dict)
    except Exception as e:
        from ...workflows.exceptions import ConfigurationError

        raise ConfigurationError(f"Invalid configuration: {e}") from e
