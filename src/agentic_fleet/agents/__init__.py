"""Agents package public API.

Avoids import-time circular dependencies by lazily resolving symbols.
"""

from __future__ import annotations

from typing import Any

__all__ = ["AgentFactory", "MagenticCoordinator"]


def __getattr__(name: str) -> Any:  # pragma: no cover - import-time behavior
    if name in {"AgentFactory", "MagenticCoordinator"}:
        from . import coordinator as _coordinator

        return getattr(_coordinator, name)
    raise AttributeError(name)
