"""Workflow agents package - re-exports from canonical agents package.

This package exists for backward compatibility. All agent creation functionality
has been moved to agentic_fleet.agents. Use that package directly instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...agents import create_workflow_agents, validate_tool

# Re-export for backward compatibility
from ...agents import create_workflow_agents, validate_tool

__all__ = ["create_workflow_agents", "validate_tool"]
