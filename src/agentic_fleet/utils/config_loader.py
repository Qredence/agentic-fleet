"""Configuration loader for workflow settings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .config_schema import validate_config

logger = logging.getLogger(__name__)


def _package_root() -> Path:
    """Return the installed package root (agentic_fleet folder)."""
    # utils/ -> agentic_fleet/
    return Path(__file__).resolve().parent.parent


def load_config(config_path: str | None = None, validate: bool = True) -> dict[str, Any]:
    """
    Load and validate configuration from YAML file.

    Args:
        config_path: Path to config file (defaults to config/workflow_config.yaml)
        validate: Whether to validate configuration schema (default: True)

    Returns:
        Dictionary with configuration settings (validated if validate=True)

    Raises:
        ConfigurationError: If validation fails and validate=True
    """
    if config_path is None:
        # Prefer CWD-relative if present, otherwise fall back to packaged config
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
                # Validate defaults but always return the original defaults
                # to preserve strict equality with get_default_config() in tests.
                validate_config(default_config)
            except Exception as e:
                from ..workflows.exceptions import ConfigurationError

                raise ConfigurationError(
                    f"Default configuration validation failed: {e}. "
                    "This indicates an issue with the built-in defaults."
                ) from e
        return default_config

    try:
        with open(config_file) as f:
            config_dict = yaml.safe_load(f)

        if not config_dict:
            logger.warning(f"Config file {config_file} is empty, using built-in defaults")
            config_dict = get_default_config()

        # Validate configuration schema
        if validate:
            try:
                validated = validate_config(config_dict)
                logger.info(f"Loaded and validated configuration from {config_file}")
                return validated.to_dict()
            except Exception as e:
                from ..workflows.exceptions import ConfigurationError

                # Provide detailed error message
                error_msg = (
                    f"Configuration validation failed for {config_file}: {e}\n"
                    "Please check the configuration file for invalid values or missing required fields."
                )
                logger.error(error_msg)
                raise ConfigurationError(error_msg, config_key=str(config_file)) from e

        logger.info(f"Loaded configuration from {config_file} (validation skipped)")
        return config_dict
    except Exception as e:
        from ..workflows.exceptions import ConfigurationError

        # If it's already a ConfigurationError, re-raise it
        if isinstance(e, ConfigurationError):
            raise

        # Otherwise, wrap in ConfigurationError
        error_msg = f"Failed to load config from {config_file}: {e}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg, config_key=str(config_file)) from e


def get_default_config() -> dict[str, Any]:
    """Return default configuration."""
    pkg = _package_root()
    return {
        "dspy": {
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 2000,
            "optimization": {
                "enabled": True,
                # Prefer packaged data path by default; callers may override
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
                "judge_model": None,
                "judge_reasoning_effort": "medium",
            },
            "handoffs": {
                "enabled": True,
            },
        },
        "agents": {
            "researcher": {
                "model": "gpt-4.1",
                "tools": ["TavilyMCPTool"],
                "temperature": 0.5,
            },
            "analyst": {
                "model": "gpt-4.1",
                "tools": ["HostedCodeInterpreterTool"],
                "temperature": 0.3,
            },
            "writer": {
                "model": "gpt-4.1",
                "tools": [],
                "temperature": 0.7,
            },
            "reviewer": {
                "model": "gpt-4.1",
                "tools": [],
                "temperature": 0.2,
            },
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": ".var/logs/workflow.log",
            "save_history": True,
            "history_file": ".var/logs/execution_history.jsonl",
            "verbose": True,
        },
        "openai": {
            "enable_completion_storage": False,
        },
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
        value = config.get("agents", {}).get(agent_name.lower(), {}).get("model", default)
        return str(value)
    except Exception:
        return default


def get_agent_temperature(config: dict[str, Any], agent_name: str, default: float = 0.7) -> float:
    """Get temperature for specific agent from config."""
    try:
        value = config.get("agents", {}).get(agent_name.lower(), {}).get("temperature", default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    except Exception:
        return default
