"""Configuration loading utilities for AgenticFleet.

This module provides:
- YAML configuration loading with LRU caching
- Automatic cache invalidation on file changes
- Default configuration generation
- Helper functions for accessing agent-specific settings
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .schemas import validate_config

logger = logging.getLogger(__name__)


# =============================================================================
# Path Resolution
# =============================================================================


def _package_root() -> Path:
    """Return the installed package root (agentic_fleet folder)."""
    return Path(__file__).resolve().parent.parent.parent


def get_config_path(filename: str = "workflow_config.yaml") -> Path:
    """Resolve the path to a config file within the package.

    First checks the current working directory's config/ folder,
    then falls back to the installed package's config/ folder.

    Args:
        filename: Config filename to resolve

    Returns:
        Path to the config file
    """
    cwd_path = Path.cwd() / "config" / filename
    if cwd_path.exists():
        return cwd_path
    return _package_root() / "config" / filename


# =============================================================================
# Config Loading (Internal)
# =============================================================================


def _load_config_cached(config_file_str: str, mtime: float, validate: bool) -> dict[str, Any]:
    """Internal cached config loader.

    Args:
        config_file_str: Path to config file as string
        mtime: Modification time of config file (for cache invalidation)
        validate: Whether to validate the config

    Returns:
        Loaded and optionally validated configuration dictionary

    Raises:
        ConfigurationError: If config file is invalid or validation fails
    """
    from ...workflows.exceptions import ConfigurationError

    config_file = Path(config_file_str)

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
                logger.debug(f"Loaded and validated configuration from {config_file}")
                return validated.to_dict()
            except Exception as e:
                error_msg = f"Configuration validation failed for {config_file}: {e}"
                logger.error(error_msg)
                raise ConfigurationError(error_msg, config_key=str(config_file)) from e

        logger.debug(f"Loaded configuration from {config_file} (validation skipped)")
        return config_dict
    except ConfigurationError:
        raise
    except Exception as e:
        error_msg = f"Failed to load config from {config_file}: {e}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg, config_key=str(config_file)) from e


# Cache config loads based on file path, modification time, and validation flag
# This avoids repeated YAML parsing for the same config file
# Cache size of 4 supports: main config + 3 test/dev configs
_load_config_cached_lru = lru_cache(maxsize=4)(_load_config_cached)


# =============================================================================
# Public Config Loading API
# =============================================================================


def load_config(config_path: str | None = None, validate: bool = True) -> dict[str, Any]:
    """Load and validate configuration from YAML file with caching.

    Configuration is cached based on file path and modification time to avoid
    repeated YAML parsing. Cache is automatically invalidated when the file changes.

    Args:
        config_path: Optional path to config file. If None, uses default locations.
        validate: Whether to validate the configuration with Pydantic schemas.

    Returns:
        Dictionary containing the loaded (and optionally validated) configuration.

    Raises:
        ConfigurationError: If config file is invalid or validation fails
    """
    if config_path is None:
        cwd_default = Path("config/workflow_config.yaml")
        pkg_default = _package_root() / "config" / "workflow_config.yaml"
        config_file = cwd_default if cwd_default.exists() else pkg_default
    else:
        config_file = Path(config_path)

    # Get modification time for cache invalidation
    # Use 0 if file doesn't exist (will return defaults)
    try:
        mtime = config_file.stat().st_mtime if config_file.exists() else 0.0
    except (OSError, PermissionError):
        mtime = 0.0

    return _load_config_cached_lru(str(config_file.resolve()), mtime, validate)


# =============================================================================
# Default Configuration
# =============================================================================


def get_default_config() -> dict[str, Any]:
    """Return default configuration.

    This provides a complete default configuration that can be used when
    no config file is found or as a base for customization.

    Returns:
        Dictionary containing all default configuration values
    """
    pkg = _package_root()
    return {
        "dspy": {
            "model": "gpt-4.1-mini",
            "temperature": 0.7,
            "max_tokens": 2000,
            "compiled_reasoner_path": ".var/cache/dspy/compiled_reasoner.json",
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
            "researcher": {"model": "gpt-4.1-mini", "tools": ["TavilyMCPTool"], "temperature": 0.5},
            "analyst": {
                "model": "gpt-4.1-mini",
                "tools": ["HostedCodeInterpreterTool"],
                "temperature": 0.3,
            },
            "writer": {"model": "gpt-4.1-mini", "tools": [], "temperature": 0.7},
            "reviewer": {"model": "gpt-4.1-mini", "tools": [], "temperature": 0.2},
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
            "capture_sensitive": False,
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


# =============================================================================
# Agent Configuration Helpers
# =============================================================================


def get_agent_model(config: dict[str, Any], agent_name: str, default: str = "gpt-4.1-mini") -> str:
    """Get model for specific agent from config.

    Args:
        config: Configuration dictionary
        agent_name: Name of the agent (case-insensitive)
        default: Default model if not specified

    Returns:
        Model name for the agent
    """
    try:
        return str(config.get("agents", {}).get(agent_name.lower(), {}).get("model", default))
    except Exception:
        return default


def get_agent_temperature(config: dict[str, Any], agent_name: str, default: float = 0.7) -> float:
    """Get temperature for specific agent from config.

    Args:
        config: Configuration dictionary
        agent_name: Name of the agent (case-insensitive)
        default: Default temperature if not specified

    Returns:
        Temperature value for the agent
    """
    try:
        value = config.get("agents", {}).get(agent_name.lower(), {}).get("temperature", default)
        return float(value)
    except (TypeError, ValueError):
        return default
