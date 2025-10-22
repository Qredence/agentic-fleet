"""
Workflow compatibility layer.

The legacy MultiAgentWorkflow has been removed in favour of the Magentic-based
fleet orchestrator. To experiment with a standalone dynamic workflow that
registers backbone modules (`planner`, `executor`, `verifier`, `generator`) and
optional tool-agents as first-class participants, use
`agenticfleet.workflows.dynamic`.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - expose dynamic exports to static analysers
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

_EXPORTS: dict[str, tuple[str, str]] = {
    "MagenticFleet": ("agenticfleet.fleet.magentic_fleet", "MagenticFleet"),
    "create_default_fleet": ("agenticfleet.fleet.magentic_fleet", "create_default_fleet"),
    "create_dynamic_workflow": (
        "agenticfleet.workflows._experimental_dynamic",
        "create_dynamic_workflow",
    ),
    "create_default_dynamic_participants": (
        "agenticfleet.workflows._experimental_dynamic",
        "create_default_dynamic_participants",
    ),
    "DynamicWorkflowParticipants": (
        "agenticfleet.workflows._experimental_dynamic",
        "DynamicWorkflowParticipants",
    ),
}


def __getattr__(name: str) -> Any:
    if name in _EXPORTS:
        module_name, attr_name = _EXPORTS[name]
        module = import_module(module_name)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_EXPORTS.keys()))
