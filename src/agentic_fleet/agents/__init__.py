"""
Agents module for AgenticFleet.

This module contains agent implementations and related functionality.

DEPRECATED: This module is deprecated and will be replaced by agentic_fleet.agents_pool in a future version.
The agents_pool module provides a more modular, base-class approach to agent implementation.
"""

import warnings

# Show deprecation warning
warnings.warn(
    "The agentic_fleet.agents module is deprecated and will be replaced by agentic_fleet.agents_pool in a future version. "
    "The agents_pool module provides a more modular, base-class approach to agent implementation.",
    DeprecationWarning,
    stacklevel=2
)

from agentic_fleet.agents.magentic_one import MagenticOneAgent, create_magentic_one_agent

__all__ = ["MagenticOneAgent", "create_magentic_one_agent"]
