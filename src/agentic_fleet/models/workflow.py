"""Workflow configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkflowConfig:
    """Workflow configuration from YAML."""

    id: str
    name: str
    description: str
    factory: str
    agents: dict[str, dict[str, Any]]
    manager: dict[str, Any]
