"""
Workflow compatibility layer.

The legacy MultiAgentWorkflow has been removed in favour of the Magentic-based
fleet orchestrator. Import from agenticfleet.fleet instead.
"""

from agenticfleet.fleet.magentic_fleet import MagenticFleet, create_default_fleet

__all__ = ["MagenticFleet", "create_default_fleet"]
