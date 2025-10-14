"""
AgenticFleet - A multi-agent orchestration system built with Microsoft Agent Framework.

A sophisticated multi-agent system that coordinates specialized AI agents to solve
complex tasks through dynamic delegation and collaboration.
"""

__version__ = "0.5.0"
__author__ = "Qredence"
__email__ = "contact@qredence.ai"

# Export main components for convenient imports
from agenticfleet.agents import (
    create_analyst_agent,
    create_coder_agent,
    create_orchestrator_agent,
    create_researcher_agent,
)
from agenticfleet.fleet.magentic_fleet import MagenticFleet, create_default_fleet

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "create_orchestrator_agent",
    "create_researcher_agent",
    "create_coder_agent",
    "create_analyst_agent",
    "MagenticFleet",
    "create_default_fleet",
]
