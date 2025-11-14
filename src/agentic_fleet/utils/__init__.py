"""Utilities package: compiler, config loader, logging, and tool registry.

This package provides utility functions and classes used throughout agentic_fleet,
including configuration management, DSPy compilation, caching, logging, and
tool registry functionality.

Public API:
    - ToolRegistry: Central registry for managing tool metadata
    - ToolMetadata: Metadata class for registered tools
    - TTLCache: In-memory cache with TTL support
    - compile_supervisor: Function to compile DSPy supervisor modules
    - load_config: Function to load workflow configuration
    - ExecutionMode: Enumeration of execution modes
    - RoutingDecision: Typed routing decision dataclass
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_fleet.utils.cache import TTLCache
    from agentic_fleet.utils.compiler import compile_supervisor
    from agentic_fleet.utils.config_loader import get_agent_model, load_config
    from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
    from agentic_fleet.utils.tool_registry import ToolMetadata, ToolRegistry

__all__ = [
    # Tool registry
    "ToolRegistry",
    "ToolMetadata",
    # Models
    "ExecutionMode",
    "RoutingDecision",
    # Compiler
    "compile_supervisor",
    # Config
    "load_config",
    "get_agent_model",
    # Cache
    "TTLCache",
]


def __getattr__(name: str) -> object:
    """Lazy import for public API."""
    if name in ("ToolRegistry", "ToolMetadata"):
        from agentic_fleet.utils.tool_registry import ToolMetadata, ToolRegistry

        if name == "ToolRegistry":
            return ToolRegistry
        return ToolMetadata

    if name in ("ExecutionMode", "RoutingDecision"):
        from agentic_fleet.utils.models import ExecutionMode, RoutingDecision

        if name == "ExecutionMode":
            return ExecutionMode
        return RoutingDecision

    if name == "compile_supervisor":
        from agentic_fleet.utils.compiler import compile_supervisor

        return compile_supervisor

    if name in ("load_config", "get_agent_model"):
        from agentic_fleet.utils.config_loader import get_agent_model, load_config

        if name == "load_config":
            return load_config
        return get_agent_model

    if name == "TTLCache":
        from agentic_fleet.utils.cache import TTLCache

        return TTLCache

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
