"""Configuration management for AgenticFleet.

This package provides centralized configuration handling including:
- constants: Magic numbers, paths, thresholds, and named constants
- env: Environment variable utilities and EnvConfig class
- schemas: Pydantic configuration schemas for validation
- loader: YAML config loading with caching

Usage:
    from agentic_fleet.utils.cfg import load_config, env_config
    from agentic_fleet.utils.cfg import DEFAULT_CACHE_TTL, PHASE_ANALYSIS

Or import specific submodules:
    from agentic_fleet.utils.cfg.constants import DEFAULT_CACHE_TTL
    from agentic_fleet.utils.cfg.env import EnvConfig
    from agentic_fleet.utils.cfg.schemas import WorkflowConfigSchema
    from agentic_fleet.utils.cfg.loader import load_config
"""

from __future__ import annotations

# =============================================================================
# Constants - All magic numbers and named values
# =============================================================================
from .constants import (
    # Agent names
    AGENT_ANALYST,
    AGENT_CODER,
    AGENT_COORDINATOR,
    AGENT_EXECUTOR,
    AGENT_GENERATOR,
    AGENT_JUDGE,
    AGENT_PLANNER,
    AGENT_RESEARCHER,
    AGENT_REVIEWER,
    AGENT_VERIFIER,
    AGENT_WRITER,
    # Cache
    ANALYSIS_CACHE_TTL,
    CACHE_VERSION,
    # Agents
    DEFAULT_AGENT_MODEL,
    DEFAULT_AGENT_TIMEOUT,
    DEFAULT_ANALYST_TEMPERATURE,
    DEFAULT_ANSWER_QUALITY_CACHE_PATH,
    # Browser
    DEFAULT_BROWSER_MAX_TEXT_LENGTH,
    DEFAULT_BROWSER_SELECTOR_TIMEOUT_MS,
    DEFAULT_BROWSER_TIMEOUT_MS,
    # Paths
    DEFAULT_CACHE_DIR,
    DEFAULT_CACHE_PATH,
    DEFAULT_CACHE_TTL,
    DEFAULT_CONFIG_PATH,
    DEFAULT_DATA_DIR,
    # DSPy
    DEFAULT_DSPY_CACHE_DIR,
    DEFAULT_DSPY_EXAMPLES_PATH,
    DEFAULT_DSPY_MAX_TOKENS,
    DEFAULT_DSPY_MODEL,
    DEFAULT_DSPY_TEMPERATURE,
    DEFAULT_EVALUATION_DIR,
    DEFAULT_EXAMPLES_PATH,
    # GEPA
    DEFAULT_GEPA_HISTORY_LIMIT,
    DEFAULT_GEPA_HISTORY_MIN_QUALITY,
    # Paths continued
    DEFAULT_GEPA_LOG_DIR,
    DEFAULT_GEPA_MAX_FULL_EVALS,
    DEFAULT_GEPA_MAX_METRIC_CALLS,
    DEFAULT_GEPA_PERFECT_SCORE,
    DEFAULT_GEPA_SEED,
    DEFAULT_GEPA_VAL_SPLIT,
    DEFAULT_HISTORY_FORMAT,
    DEFAULT_HISTORY_PATH,
    DEFAULT_JUDGE_TEMPERATURE,
    # Quality
    DEFAULT_JUDGE_THRESHOLD,
    DEFAULT_LOG_PATH,
    DEFAULT_LOGS_DIR,
    DEFAULT_MAX_BOOTSTRAPPED_DEMOS,
    DEFAULT_MAX_HISTORY_ENTRIES,
    DEFAULT_MAX_REFINEMENT_ROUNDS,
    DEFAULT_MAX_RESETS,
    DEFAULT_MAX_ROUNDS,
    DEFAULT_MAX_STALLS,
    DEFAULT_NLU_CACHE_PATH,
    DEFAULT_PARALLEL_THRESHOLD,
    DEFAULT_QUALITY_THRESHOLD,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_REFINEMENT_THRESHOLD,
    # UI
    DEFAULT_REFRESH_RATE,
    DEFAULT_RESEARCHER_TEMPERATURE,
    # Retries
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    DEFAULT_REVIEWER_TEMPERATURE,
    # Timeouts
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_VAR_DIR,
    DEFAULT_WORKFLOW_TIMEOUT,
    DEFAULT_WRITER_TEMPERATURE,
    # Execution modes
    EXECUTION_MODE_DELEGATED,
    EXECUTION_MODE_PARALLEL,
    EXECUTION_MODE_SEQUENTIAL,
    # Error limits
    MAX_ERROR_MESSAGE_LENGTH,
    MAX_RETRY_ATTEMPTS,
    MAX_TASK_LENGTH,
    MAX_TASK_PREVIEW_LENGTH,
    MIN_CACHE_SIZE_BYTES,
    MIN_TASK_LENGTH,
    PERFECT_SCORE,
    # Phase names
    PHASE_ANALYSIS,
    PHASE_EXECUTION,
    PHASE_JUDGE,
    PHASE_PROGRESS,
    PHASE_QUALITY,
    PHASE_REFINEMENT,
    PHASE_ROUTING,
    # Reasoning effort
    REASONING_EFFORT_MAXIMAL,
    REASONING_EFFORT_MEDIUM,
    REASONING_EFFORT_MINIMAL,
    # Serialization
    SERIALIZER_DILL,
    SERIALIZER_NONE,
    SERIALIZER_PICKLE,
    # Status values
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    STATUS_SUCCESS,
    STATUS_TIMEOUT,
    # Tool names
    TOOL_BROWSER,
    TOOL_HOSTED_CODE_INTERPRETER,
    TOOL_TAVILY_MCP,
    TOOL_TAVILY_SEARCH,
)

# =============================================================================
# Environment Utilities
# =============================================================================
from .env import (
    EnvConfig,
    env_config,
    get_env_bool,
    get_env_float,
    get_env_int,
    get_env_var,
    validate_agentic_fleet_env,
    validate_required_env_vars,
)

# =============================================================================
# Configuration Loading
# =============================================================================
from .loader import (
    get_agent_model,
    get_agent_temperature,
    get_config_path,
    get_default_config,
    load_config,
)

# =============================================================================
# Configuration Schemas
# =============================================================================
from .schemas import (
    AgentConfig,
    AgentsConfig,
    DSPyConfig,
    DSPyOptimizationConfig,
    EvaluationConfig,
    ExecutionConfig,
    HandoffConfig,
    LoggingConfig,
    OpenAIConfig,
    QualityConfig,
    SupervisorConfig,
    ToolsConfig,
    TracingConfig,
    WorkflowConfig,
    WorkflowConfigSchema,
    validate_config,
)

__all__ = [
    "AGENT_ANALYST",
    "AGENT_CODER",
    "AGENT_COORDINATOR",
    "AGENT_EXECUTOR",
    "AGENT_GENERATOR",
    "AGENT_JUDGE",
    "AGENT_PLANNER",
    # Constants - Agent names
    "AGENT_RESEARCHER",
    "AGENT_REVIEWER",
    "AGENT_VERIFIER",
    "AGENT_WRITER",
    "ANALYSIS_CACHE_TTL",
    "CACHE_VERSION",
    # Constants - Agent
    "DEFAULT_AGENT_MODEL",
    "DEFAULT_AGENT_TIMEOUT",
    "DEFAULT_ANALYST_TEMPERATURE",
    "DEFAULT_ANSWER_QUALITY_CACHE_PATH",
    "DEFAULT_BROWSER_MAX_TEXT_LENGTH",
    "DEFAULT_BROWSER_SELECTOR_TIMEOUT_MS",
    # Constants - Browser
    "DEFAULT_BROWSER_TIMEOUT_MS",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_CACHE_PATH",
    # Constants - Cache
    "DEFAULT_CACHE_TTL",
    # Constants - Paths
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_DATA_DIR",
    "DEFAULT_DSPY_CACHE_DIR",
    "DEFAULT_DSPY_EXAMPLES_PATH",
    "DEFAULT_DSPY_MAX_TOKENS",
    # Constants - DSPy
    "DEFAULT_DSPY_MODEL",
    "DEFAULT_DSPY_TEMPERATURE",
    "DEFAULT_EVALUATION_DIR",
    "DEFAULT_EXAMPLES_PATH",
    "DEFAULT_GEPA_HISTORY_LIMIT",
    "DEFAULT_GEPA_HISTORY_MIN_QUALITY",
    "DEFAULT_GEPA_LOG_DIR",
    "DEFAULT_GEPA_MAX_FULL_EVALS",
    "DEFAULT_GEPA_MAX_METRIC_CALLS",
    "DEFAULT_GEPA_PERFECT_SCORE",
    "DEFAULT_GEPA_SEED",
    # Constants - GEPA
    "DEFAULT_GEPA_VAL_SPLIT",
    # Constants - History
    "DEFAULT_HISTORY_FORMAT",
    "DEFAULT_HISTORY_PATH",
    "DEFAULT_JUDGE_TEMPERATURE",
    "DEFAULT_JUDGE_THRESHOLD",
    "DEFAULT_LOGS_DIR",
    "DEFAULT_LOG_PATH",
    "DEFAULT_MAX_BOOTSTRAPPED_DEMOS",
    "DEFAULT_MAX_HISTORY_ENTRIES",
    "DEFAULT_MAX_REFINEMENT_ROUNDS",
    "DEFAULT_MAX_RESETS",
    # Constants - Workflow
    "DEFAULT_MAX_ROUNDS",
    "DEFAULT_MAX_STALLS",
    "DEFAULT_NLU_CACHE_PATH",
    "DEFAULT_PARALLEL_THRESHOLD",
    # Constants - Quality
    "DEFAULT_QUALITY_THRESHOLD",
    "DEFAULT_REASONING_EFFORT",
    "DEFAULT_REFINEMENT_THRESHOLD",
    # Constants - UI
    "DEFAULT_REFRESH_RATE",
    "DEFAULT_RESEARCHER_TEMPERATURE",
    # Constants - Retries
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "DEFAULT_REVIEWER_TEMPERATURE",
    # Constants - Timeouts
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_VAR_DIR",
    "DEFAULT_WORKFLOW_TIMEOUT",
    "DEFAULT_WRITER_TEMPERATURE",
    # Constants - Execution modes
    "EXECUTION_MODE_DELEGATED",
    "EXECUTION_MODE_PARALLEL",
    "EXECUTION_MODE_SEQUENTIAL",
    "MAX_ERROR_MESSAGE_LENGTH",
    "MAX_RETRY_ATTEMPTS",
    # Constants - Task validation
    "MAX_TASK_LENGTH",
    # Constants - Error limits
    "MAX_TASK_PREVIEW_LENGTH",
    "MIN_CACHE_SIZE_BYTES",
    "MIN_TASK_LENGTH",
    "PERFECT_SCORE",
    # Constants - Phase names
    "PHASE_ANALYSIS",
    "PHASE_EXECUTION",
    "PHASE_JUDGE",
    "PHASE_PROGRESS",
    "PHASE_QUALITY",
    "PHASE_REFINEMENT",
    "PHASE_ROUTING",
    "REASONING_EFFORT_MAXIMAL",
    "REASONING_EFFORT_MEDIUM",
    # Constants - Reasoning
    "REASONING_EFFORT_MINIMAL",
    "SERIALIZER_DILL",
    "SERIALIZER_NONE",
    # Constants - Serialization
    "SERIALIZER_PICKLE",
    "STATUS_FAILED",
    "STATUS_IN_PROGRESS",
    "STATUS_PENDING",
    # Constants - Status values
    "STATUS_SUCCESS",
    "STATUS_TIMEOUT",
    "TOOL_BROWSER",
    "TOOL_HOSTED_CODE_INTERPRETER",
    # Constants - Tool names
    "TOOL_TAVILY_MCP",
    "TOOL_TAVILY_SEARCH",
    "AgentConfig",
    "AgentsConfig",
    "DSPyConfig",
    # Schemas
    "DSPyOptimizationConfig",
    "EnvConfig",
    "EvaluationConfig",
    "ExecutionConfig",
    "HandoffConfig",
    "LoggingConfig",
    "OpenAIConfig",
    "QualityConfig",
    "SupervisorConfig",
    "ToolsConfig",
    "TracingConfig",
    "WorkflowConfig",
    "WorkflowConfigSchema",
    "env_config",
    "get_agent_model",
    "get_agent_temperature",
    # Loader
    "get_config_path",
    "get_default_config",
    "get_env_bool",
    "get_env_float",
    "get_env_int",
    # Environment utilities
    "get_env_var",
    "load_config",
    "validate_agentic_fleet_env",
    "validate_config",
    "validate_required_env_vars",
]
