"""Configuration management for AgenticFleet.

Consolidated from:
- config_loader.py (YAML loading and defaults)
- config_schema.py (Pydantic validation schemas)
- constants.py (magic numbers and strings)
- env.py (environment variable utilities)

This module provides:
- YAML config loading with validation
- Environment variable utilities
- Centralized constants
- Pydantic config schemas
"""

# ruff: noqa: D102

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Task validation
MAX_TASK_LENGTH = 10000
MIN_TASK_LENGTH = 1

# Cache
DEFAULT_CACHE_TTL = 300
ANALYSIS_CACHE_TTL = 3600
CACHE_VERSION = 2
MIN_CACHE_SIZE_BYTES = 64

# Timeouts
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_AGENT_TIMEOUT = 300
DEFAULT_WORKFLOW_TIMEOUT = 600

# Retries
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0
MAX_RETRY_ATTEMPTS = 5

# Quality thresholds
DEFAULT_QUALITY_THRESHOLD = 8.0
DEFAULT_JUDGE_THRESHOLD = 7.0
DEFAULT_REFINEMENT_THRESHOLD = 8.0
PERFECT_SCORE = 10.0

# Workflow limits
DEFAULT_MAX_ROUNDS = 15
DEFAULT_MAX_STALLS = 3
DEFAULT_MAX_RESETS = 2
DEFAULT_MAX_REFINEMENT_ROUNDS = 2
DEFAULT_PARALLEL_THRESHOLD = 3

# DSPy
DEFAULT_DSPY_MODEL = "gpt-5-mini"
DEFAULT_DSPY_TEMPERATURE = 0.7
DEFAULT_DSPY_MAX_TOKENS = 2000
DEFAULT_MAX_BOOTSTRAPPED_DEMOS = 4

# Agent temperatures
DEFAULT_AGENT_MODEL = "gpt-4.1"
DEFAULT_RESEARCHER_TEMPERATURE = 0.5
DEFAULT_ANALYST_TEMPERATURE = 0.3
DEFAULT_WRITER_TEMPERATURE = 0.7
DEFAULT_REVIEWER_TEMPERATURE = 0.2
DEFAULT_JUDGE_TEMPERATURE = 0.4

# Reasoning effort
REASONING_EFFORT_MINIMAL = "minimal"
REASONING_EFFORT_MEDIUM = "medium"
REASONING_EFFORT_MAXIMAL = "maximal"
DEFAULT_REASONING_EFFORT = REASONING_EFFORT_MEDIUM

# Execution modes
EXECUTION_MODE_DELEGATED = "delegated"
EXECUTION_MODE_SEQUENTIAL = "sequential"
EXECUTION_MODE_PARALLEL = "parallel"

# File paths
DEFAULT_CONFIG_PATH = "config/workflow_config.yaml"
DEFAULT_EXAMPLES_PATH = "src/agentic_fleet/data/supervisor_examples.json"
DEFAULT_VAR_DIR = ".var"
DEFAULT_CACHE_DIR = ".var/cache"
DEFAULT_LOGS_DIR = ".var/logs"
DEFAULT_DATA_DIR = ".var/data"
DEFAULT_CACHE_PATH = ".var/logs/compiled_supervisor.pkl"
DEFAULT_ANSWER_QUALITY_CACHE_PATH = ".var/logs/compiled_answer_quality.pkl"
DEFAULT_NLU_CACHE_PATH = ".var/logs/compiled_nlu.pkl"
DEFAULT_HISTORY_PATH = ".var/logs/execution_history.jsonl"
DEFAULT_LOG_PATH = ".var/logs/workflow.log"
DEFAULT_GEPA_LOG_DIR = ".var/logs/gepa"
DEFAULT_DSPY_CACHE_DIR = ".var/cache/dspy"
DEFAULT_DSPY_EXAMPLES_PATH = ".var/logs/dspy_examples.jsonl"
DEFAULT_EVALUATION_DIR = ".var/logs/evaluation"

# History
DEFAULT_HISTORY_FORMAT = "jsonl"
DEFAULT_MAX_HISTORY_ENTRIES = 1000

# UI
DEFAULT_REFRESH_RATE = 4

# Error limits
MAX_TASK_PREVIEW_LENGTH = 100
MAX_ERROR_MESSAGE_LENGTH = 500

# Browser tool
DEFAULT_BROWSER_TIMEOUT_MS = 30000
DEFAULT_BROWSER_SELECTOR_TIMEOUT_MS = 5000
DEFAULT_BROWSER_MAX_TEXT_LENGTH = 10000

# GEPA optimizer
DEFAULT_GEPA_VAL_SPLIT = 0.2
DEFAULT_GEPA_SEED = 13
DEFAULT_GEPA_HISTORY_MIN_QUALITY = 8.0
DEFAULT_GEPA_HISTORY_LIMIT = 200
DEFAULT_GEPA_MAX_FULL_EVALS = 50
DEFAULT_GEPA_MAX_METRIC_CALLS = 150
DEFAULT_GEPA_PERFECT_SCORE = 1.0

# Agent names
AGENT_RESEARCHER = "Researcher"
AGENT_ANALYST = "Analyst"
AGENT_WRITER = "Writer"
AGENT_REVIEWER = "Reviewer"
AGENT_JUDGE = "Judge"
AGENT_PLANNER = "Planner"
AGENT_EXECUTOR = "Executor"
AGENT_CODER = "Coder"
AGENT_VERIFIER = "Verifier"
AGENT_GENERATOR = "Generator"
AGENT_COORDINATOR = "Coordinator"

# Tool names
TOOL_TAVILY_MCP = "TavilyMCPTool"
TOOL_TAVILY_SEARCH = "TavilySearchTool"
TOOL_BROWSER = "BrowserTool"
TOOL_HOSTED_CODE_INTERPRETER = "HostedCodeInterpreterTool"

# Phase names
PHASE_ANALYSIS = "analysis"
PHASE_ROUTING = "routing"
PHASE_EXECUTION = "execution"
PHASE_PROGRESS = "progress"
PHASE_QUALITY = "quality"
PHASE_JUDGE = "judge"
PHASE_REFINEMENT = "refinement"

# Status values
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_TIMEOUT = "timeout"

# Serialization
SERIALIZER_PICKLE = "pickle"
SERIALIZER_DILL = "dill"
SERIALIZER_NONE = "none"


# =============================================================================
# Environment Variable Utilities
# =============================================================================

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def get_env_var(name: str, default: str | None = None, required: bool = False) -> str:
    """Get environment variable with optional validation."""
    from ..workflows.exceptions import ConfigurationError

    value = os.getenv(name, default)
    if required and (not value or not value.strip()):
        error_msg = f"Required environment variable {name} is not set"
        logger.error(error_msg)
        raise ConfigurationError(error_msg, config_key="environment")
    return value or ""


def get_env_bool(name: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    value = os.getenv(name, "").strip().lower()
    return value in _TRUTHY_VALUES if value else default


def get_env_int(name: str, default: int = 0) -> int:
    """Get environment variable as integer."""
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for {name}: '{value}', using default {default}")
        return default


def get_env_float(name: str, default: float = 0.0) -> float:
    """Get environment variable as float."""
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid float value for {name}: '{value}', using default {default}")
        return default


class EnvConfig:
    """Centralized, type-safe access to AgenticFleet environment variables.

    Property accessors expose individual env vars with caching. Each property
    name corresponds to its environment variable counterpart (snake_case).
    Docstrings are intentionally omitted on trivial getters.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    def _get_cached(self, key: str, loader: Any) -> Any:
        if key not in self._cache:
            self._cache[key] = loader()
        return self._cache[key]

    @property
    def openai_api_key(self) -> str:
        return self._get_cached("openai_api_key", lambda: get_env_var("OPENAI_API_KEY", ""))

    @property
    def openai_base_url(self) -> str | None:
        def _load() -> str | None:
            value = get_env_var("OPENAI_BASE_URL", "")
            return value if value else None

        return self._get_cached("openai_base_url", _load)

    @property
    def tavily_api_key(self) -> str:
        return self._get_cached("tavily_api_key", lambda: get_env_var("TAVILY_API_KEY", ""))

    @property
    def log_format(self) -> str:
        return self._get_cached("log_format", lambda: get_env_var("LOG_FORMAT", "text").lower())

    @property
    def enable_dspy_agents(self) -> bool:
        return self._get_cached(
            "enable_dspy_agents", lambda: get_env_bool("ENABLE_DSPY_AGENTS", default=True)
        )

    @property
    def mlflow_dspy_autolog(self) -> bool:
        return self._get_cached(
            "mlflow_dspy_autolog", lambda: get_env_bool("MLFLOW_DSPY_AUTOLOG", default=False)
        )

    @property
    def use_cosmos(self) -> bool:
        return self._get_cached(
            "use_cosmos", lambda: get_env_bool("AGENTICFLEET_USE_COSMOS", default=False)
        )

    @property
    def cosmos_endpoint(self) -> str:
        return self._get_cached("cosmos_endpoint", lambda: get_env_var("AZURE_COSMOS_ENDPOINT", ""))

    @property
    def cosmos_key(self) -> str:
        return self._get_cached("cosmos_key", lambda: get_env_var("AZURE_COSMOS_KEY", ""))

    @property
    def cosmos_database(self) -> str:
        return self._get_cached(
            "cosmos_database", lambda: get_env_var("AZURE_COSMOS_DATABASE", "agentic-fleet")
        )

    @property
    def cosmos_use_managed_identity(self) -> bool:
        return self._get_cached(
            "cosmos_use_managed_identity",
            lambda: get_env_bool("AZURE_COSMOS_USE_MANAGED_IDENTITY", default=False),
        )

    @property
    def otel_exporter_endpoint(self) -> str | None:
        def _load() -> str | None:
            value = get_env_var("OTEL_EXPORTER_OTLP_ENDPOINT", "")
            return value if value else None

        return self._get_cached("otel_exporter_endpoint", _load)

    @property
    def host(self) -> str:
        return self._get_cached("host", lambda: get_env_var("HOST", "0.0.0.0"))

    @property
    def port(self) -> int:
        return self._get_cached("port", lambda: get_env_int("PORT", default=8000))

    @property
    def environment(self) -> str:
        return self._get_cached("environment", lambda: get_env_var("ENVIRONMENT", "development"))

    def clear_cache(self) -> None:
        self._cache.clear()


env_config = EnvConfig()


def validate_required_env_vars(
    required_vars: list[str], optional_vars: list[str] | None = None
) -> None:
    """Validate that required environment variables are set."""
    from ..workflows.exceptions import ConfigurationError

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or not value.strip():
            missing.append(var)

    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg, config_key="environment")

    if optional_vars:
        for var in optional_vars:
            value = os.getenv(var)
            if not value:
                logger.debug(f"Optional environment variable {var} is not set")


def validate_agentic_fleet_env() -> None:
    """Validate environment variables required for AgenticFleet."""
    required = ["OPENAI_API_KEY"]
    optional = ["TAVILY_API_KEY", "OPENAI_BASE_URL", "HOST", "PORT", "ENVIRONMENT"]
    validate_required_env_vars(required, optional)

    if env_config.use_cosmos:
        cosmos_required = ["AZURE_COSMOS_ENDPOINT", "AZURE_COSMOS_DATABASE"]
        if not env_config.cosmos_use_managed_identity:
            cosmos_required.append("AZURE_COSMOS_KEY")
        validate_required_env_vars(cosmos_required, [])
        logger.info("Cosmos DB integration enabled for database '%s'", env_config.cosmos_database)

    logger.info("Environment variable validation passed")


# =============================================================================
# Pydantic Configuration Schemas
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


class DSPyConfig(BaseModel):
    """DSPy configuration."""

    model: str = "gpt-5-mini"
    routing_model: str | None = None  # Optional fast model for routing/analysis
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=1, le=32000)
    require_compiled: bool = False
    # DSPy 3.x TypedPredictor settings for structured outputs
    use_typed_signatures: bool = True  # Enable Pydantic-based typed signatures
    enable_routing_cache: bool = True  # Cache routing decisions
    routing_cache_ttl_seconds: int = Field(default=300, ge=0)  # Cache TTL in seconds
    optimization: DSPyOptimizationConfig = DSPyOptimizationConfig()


class SupervisorConfig(BaseModel):
    """Supervisor configuration."""

    max_rounds: int = Field(default=15, ge=1, le=100)
    max_stalls: int = Field(default=3, ge=1, le=20)
    max_resets: int = Field(default=2, ge=0, le=10)
    enable_streaming: bool = True
    pipeline_profile: Literal["full", "light"] = "full"
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

    model_config = ConfigDict(extra="allow")


class AgentsConfig(BaseModel):
    """Agents configuration."""

    researcher: AgentConfig = AgentConfig()
    analyst: AgentConfig = AgentConfig()
    writer: AgentConfig = AgentConfig()
    reviewer: AgentConfig = AgentConfig()

    model_config = ConfigDict(extra="allow")


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


class OpenAIConfig(BaseModel):
    """OpenAI configuration."""

    enable_completion_storage: bool = False


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
        return cls.model_validate(config_dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def validate_config(config_dict: dict[str, Any]) -> WorkflowConfigSchema:
    """Validate configuration dictionary."""
    try:
        return WorkflowConfigSchema.from_dict(config_dict)
    except Exception as e:
        from ..workflows.exceptions import ConfigurationError

        raise ConfigurationError(f"Invalid configuration: {e}") from e


# =============================================================================
# Config Loading
# =============================================================================


def _package_root() -> Path:
    """Return the installed package root (agentic_fleet folder)."""
    return Path(__file__).resolve().parent.parent


def get_config_path(filename: str = "workflow_config.yaml") -> Path:
    """Resolve the path to a config file within the package."""
    cwd_path = Path.cwd() / "config" / filename
    if cwd_path.exists():
        return cwd_path
    return _package_root() / "config" / filename


def load_config(config_path: str | None = None, validate: bool = True) -> dict[str, Any]:
    """Load and validate configuration from YAML file."""
    from ..workflows.exceptions import ConfigurationError

    if config_path is None:
        cwd_default = Path("config/workflow_config.yaml")
        pkg_default = _package_root() / "config" / "workflow_config.yaml"
        config_file = cwd_default if cwd_default.exists() else pkg_default
    else:
        config_file = Path(config_path)

    if not config_file.exists():
        logger.warning(f"Config file not found at {config_file}, using built-in defaults")
        default_config = get_default_config()
        if validate:
            try:
                validate_config(default_config)
            except Exception as e:
                raise ConfigurationError(f"Default configuration validation failed: {e}") from e
        return default_config

    try:
        with open(config_file) as f:
            config_dict = yaml.safe_load(f)

        if not config_dict:
            logger.warning(f"Config file {config_file} is empty, using built-in defaults")
            config_dict = get_default_config()

        if validate:
            try:
                validated = validate_config(config_dict)
                logger.info(f"Loaded and validated configuration from {config_file}")
                return validated.to_dict()
            except Exception as e:
                error_msg = f"Configuration validation failed for {config_file}: {e}"
                logger.error(error_msg)
                raise ConfigurationError(error_msg, config_key=str(config_file)) from e

        logger.info(f"Loaded configuration from {config_file} (validation skipped)")
        return config_dict
    except ConfigurationError:
        raise
    except Exception as e:
        error_msg = f"Failed to load config from {config_file}: {e}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg, config_key=str(config_file)) from e


def get_default_config() -> dict[str, Any]:
    """Return default configuration."""
    pkg = _package_root()
    return {
        "dspy": {
            "model": "gpt-4.1",
            "temperature": 0.7,
            "max_tokens": 2000,
            "optimization": {
                "enabled": True,
                "examples_path": str(pkg / "data" / "supervisor_examples.json"),
                "metric_threshold": 0.8,
                "max_bootstrapped_demos": 4,
                "use_gepa": False,
                "gepa_auto": "light",
                "gepa_max_full_evals": 50,
                "gepa_max_metric_calls": 150,
                "gepa_reflection_model": None,
                "gepa_log_dir": ".var/logs/gepa",
                "gepa_perfect_score": 1.0,
                "gepa_use_history_examples": False,
                "gepa_history_min_quality": 8.0,
                "gepa_history_limit": 200,
                "gepa_val_split": 0.2,
                "gepa_seed": 13,
            },
        },
        "workflow": {
            "supervisor": {
                "max_rounds": 15,
                "max_stalls": 3,
                "max_resets": 2,
                "enable_streaming": True,
                "pipeline_profile": "full",
                "simple_task_max_words": 40,
            },
            "execution": {
                "parallel_threshold": 3,
                "timeout_seconds": 300,
                "retry_attempts": 2,
            },
            "quality": {
                "refinement_threshold": 8.0,
                "enable_refinement": True,
                "enable_progress_eval": True,
                "enable_quality_eval": True,
                "judge_threshold": 7.0,
                "enable_judge": True,
                "max_refinement_rounds": 2,
                "judge_model": None,
                "judge_reasoning_effort": "medium",
            },
            "handoffs": {"enabled": True},
        },
        "agents": {
            "researcher": {"model": "gpt-4.1", "tools": ["TavilyMCPTool"], "temperature": 0.5},
            "analyst": {
                "model": "gpt-4.1",
                "tools": ["HostedCodeInterpreterTool"],
                "temperature": 0.3,
            },
            "writer": {"model": "gpt-4.1", "tools": [], "temperature": 0.7},
            "reviewer": {"model": "gpt-4.1", "tools": [], "temperature": 0.2},
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": ".var/logs/workflow.log",
            "save_history": True,
            "history_file": ".var/logs/execution_history.jsonl",
            "verbose": True,
        },
        "openai": {"enable_completion_storage": False},
        "tracing": {
            "enabled": False,
            "otlp_endpoint": "http://localhost:4317",
            "capture_sensitive": True,
        },
        "evaluation": {
            "enabled": False,
            "dataset_path": str(pkg / "data" / "evaluation_tasks.jsonl"),
            "output_dir": ".var/logs/evaluation",
            "metrics": [
                "quality_score",
                "keyword_success",
                "latency_seconds",
                "routing_efficiency",
                "refinement_triggered",
            ],
            "max_tasks": 0,
            "stop_on_failure": False,
        },
    }


def get_agent_model(config: dict[str, Any], agent_name: str, default: str = "gpt-4.1") -> str:
    """Get model for specific agent from config."""
    try:
        return str(config.get("agents", {}).get(agent_name.lower(), {}).get("model", default))
    except Exception:
        return default


def get_agent_temperature(config: dict[str, Any], agent_name: str, default: float = 0.7) -> float:
    """Get temperature for specific agent from config."""
    try:
        value = config.get("agents", {}).get(agent_name.lower(), {}).get("temperature", default)
        return float(value)
    except (TypeError, ValueError):
        return default
