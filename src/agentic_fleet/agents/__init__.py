"""Agents package public API.

Exports AgentFactory for creating ChatAgent instances from YAML configuration.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .coordinator import AgentFactory

__all__ = ["AgentFactory"]


def __getattr__(name: str) -> Any:
    if name == "AgentFactory":
        from . import coordinator as _coordinator

        return getattr(_coordinator, name)
    raise AttributeError(name)
