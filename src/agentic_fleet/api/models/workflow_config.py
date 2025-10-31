"""Workflow configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkflowConfig:
    """Configuration for a workflow definition."""

    id: str
    name: str
    description: str
    factory: str
    agents: dict[str, Any]
    manager: dict[str, Any]
