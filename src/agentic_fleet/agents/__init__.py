"""Agents package public API.

Avoids import-time circular dependencies by lazily resolving symbols while
remaining friendly to static type checkers (pyright/mypy) via TYPE_CHECKING
imports. This prevents early environment validation failures (e.g. missing
OPENAI_API_KEY) when the package is imported purely for introspection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import-time only for type checkers
    from .coordinator import AgentFactory, MagenticCoordinator

__all__ = ["AgentFactory", "MagenticCoordinator"]


def __getattr__(name: str) -> Any:  # pragma: no cover - runtime lazy import
    if name in {"AgentFactory", "MagenticCoordinator"}:
        from . import coordinator as _coordinator

        return getattr(_coordinator, name)
    raise AttributeError(name)
