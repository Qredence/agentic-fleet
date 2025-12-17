"""Core configuration for AgenticFleet.

This module provides unified configuration access for the entire application,
consolidating:
- FastAPI app settings (from app/settings.py)
- Workflow configuration (from utils/config.py)
- Environment variable utilities

Usage:
    from agentic_fleet.core.config import get_settings, load_workflow_config, env_config

    # FastAPI settings
    settings = get_settings()
    print(settings.app_name)

    # Workflow config
    config = load_workflow_config()
    print(config["dspy"]["model"])

    # Environment access
    print(env_config.openai_api_key)
"""

from __future__ import annotations

# Re-export FastAPI settings from core/settings.py
from agentic_fleet.core.settings import AppSettings, get_settings

# Re-export everything from utils/cfg for backward compatibility
from agentic_fleet.utils.cfg import (
    # Constants
    DEFAULT_AGENT_MODEL,
    DEFAULT_CACHE_DIR,
    DEFAULT_CACHE_TTL,
    DEFAULT_DATA_DIR,
    DEFAULT_DSPY_MODEL,
    DEFAULT_HISTORY_PATH,
    DEFAULT_LOGS_DIR,
    DEFAULT_VAR_DIR,
    AgentConfig,
    AgentsConfig,
    DSPyConfig,
    DSPyOptimizationConfig,
    # Environment utilities
    EnvConfig,
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
    env_config,
    # Config loading
    get_agent_model,
    get_agent_temperature,
    get_config_path,
    get_default_config,
    get_env_bool,
    get_env_float,
    get_env_int,
    get_env_var,
    load_config,
    validate_agentic_fleet_env,
    validate_config,
    validate_required_env_vars,
)

# Alias for consistency
load_workflow_config = load_config

__all__ = [
    "DEFAULT_AGENT_MODEL",
    "DEFAULT_CACHE_DIR",
    # Constants (commonly used)
    "DEFAULT_CACHE_TTL",
    "DEFAULT_DATA_DIR",
    "DEFAULT_DSPY_MODEL",
    "DEFAULT_HISTORY_PATH",
    "DEFAULT_LOGS_DIR",
    "DEFAULT_VAR_DIR",
    "AgentConfig",
    "AgentsConfig",
    # FastAPI Settings
    "AppSettings",
    "DSPyConfig",
    "DSPyOptimizationConfig",
    # Environment
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
    # Config Schemas
    "WorkflowConfigSchema",
    "env_config",
    "get_agent_model",
    "get_agent_temperature",
    "get_config_path",
    "get_default_config",
    "get_env_bool",
    "get_env_float",
    "get_env_int",
    "get_env_var",
    "get_settings",
    # Workflow Config
    "load_config",
    "load_workflow_config",
    "validate_agentic_fleet_env",
    "validate_config",
    "validate_required_env_vars",
]
