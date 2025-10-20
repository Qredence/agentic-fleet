"""
Workflow compatibility layer.

The legacy MultiAgentWorkflow has been removed in favour of the Magentic-based
fleet orchestrator. To experiment with a standalone dynamic workflow that
registers backbone modules (`planner`, `executor`, `verifier`, `generator`) and
optional tool-agents as first-class participants, use
`agenticfleet.workflows.dynamic`.
"""

from agenticfleet.fleet.magentic_fleet import MagenticFleet, create_default_fleet
from agenticfleet.workflows._experimental_dynamic import (
    DynamicWorkflowParticipants,
    create_default_dynamic_participants,
    create_dynamic_workflow,
)

__all__ = [
    "MagenticFleet",
    "create_default_fleet",
    "create_dynamic_workflow",
    "create_default_dynamic_participants",
    "DynamicWorkflowParticipants",
]
