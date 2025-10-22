"""
AgenticFleet - A multi-agent orchestration system built with Microsoft Agent Framework.

A sophisticated multi-agent system that coordinates specialized AI agents to solve
complex tasks through dynamic delegation and collaboration.
"""

__version__ = "0.5.1"
__author__ = "Qredence"
__email__ = "contact@qredence.ai"

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - for static analyzers
    from agenticfleet.agents import (
        create_analyst_agent,
        create_coder_agent,
        create_orchestrator_agent,
        create_researcher_agent,
    )
    from agenticfleet.fleet.magentic_fleet import MagenticFleet, create_default_fleet
    from agenticfleet.observability import get_trace_config, is_tracing_enabled, setup_tracing

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
    "setup_tracing",
    "is_tracing_enabled",
    "get_trace_config",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "create_orchestrator_agent": ("agenticfleet.agents", "create_orchestrator_agent"),
    "create_researcher_agent": ("agenticfleet.agents", "create_researcher_agent"),
    "create_coder_agent": ("agenticfleet.agents", "create_coder_agent"),
    "create_analyst_agent": ("agenticfleet.agents", "create_analyst_agent"),
    "MagenticFleet": ("agenticfleet.fleet.magentic_fleet", "MagenticFleet"),
    "create_default_fleet": ("agenticfleet.fleet.magentic_fleet", "create_default_fleet"),
    "setup_tracing": ("agenticfleet.observability", "setup_tracing"),
    "is_tracing_enabled": ("agenticfleet.observability", "is_tracing_enabled"),
    "get_trace_config": ("agenticfleet.observability", "get_trace_config"),
}


def __getattr__(name: str) -> Any:
    if name in _EXPORTS:
        module_name, attr_name = _EXPORTS[name]
        module = import_module(module_name)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_EXPORTS.keys()))
