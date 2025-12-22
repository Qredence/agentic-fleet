"""Configuration loading utilities."""

from __future__ import annotations

from typing import Any

from agentic_fleet.utils.cfg.loader import load_yaml_config
from agentic_fleet.utils.cfg.schemas import WorkflowConfigSchema


def load_workflow_config(path: str) -> WorkflowConfigSchema:
    """Load and validate workflow configuration from YAML file.

    Args:
        path: Path to YAML configuration file

    Returns:
        Validated configuration schema
    """
    raw_config = load_yaml_config(path)
    return WorkflowConfigSchema.from_dict(raw_config)


def load_config(path: str) -> dict[str, Any]:
    """Load raw configuration from YAML file (legacy support)."""
    return load_yaml_config(path)
