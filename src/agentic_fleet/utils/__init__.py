"""Utilities package: compiler, config loader, logging, tracing, and tool registry.

This package provides utility functions and classes used throughout agentic_fleet,
including configuration management, DSPy compilation, caching, logging, tracing,
and tool registry functionality.

Public API:
    - ToolRegistry: Central registry for managing tool metadata
    - ToolMetadata: Metadata class for registered tools
    - TTLCache: In-memory cache with TTL support
    - compile_supervisor: Function to compile DSPy supervisor modules
    - load_config: Function to load workflow configuration
    - ExecutionMode: Enumeration of execution modes
    - RoutingDecision: Typed routing decision dataclass
    - initialize_tracing: Initialize OpenTelemetry tracing
    - get_tracer: Get a tracer for custom spans
    - get_meter: Get a meter for custom metrics
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_fleet.utils.cache import TTLCache
    from agentic_fleet.utils.compiler import compile_reasoner
    from agentic_fleet.utils.config_loader import get_agent_model, load_config
    from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
    from agentic_fleet.utils.tool_registry import ToolMetadata, ToolRegistry
    from agentic_fleet.utils.tracing import get_meter, get_tracer, initialize_tracing

__all__ = [
    "ExecutionMode",
    "RoutingDecision",
    "TTLCache",
    "ToolMetadata",
    "ToolRegistry",
    "compile_reasoner",
    "get_agent_model",
    "get_meter",
    "get_tracer",
    "initialize_tracing",
    "load_config",
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

    if name == "compile_reasoner":
        from agentic_fleet.utils.compiler import compile_reasoner

        return compile_reasoner

    if name in ("load_config", "get_agent_model"):
        from agentic_fleet.utils.config_loader import get_agent_model, load_config

        if name == "load_config":
            return load_config
        return get_agent_model

    if name == "TTLCache":
        from agentic_fleet.utils.cache import TTLCache

        return TTLCache

    if name in ("initialize_tracing", "get_tracer", "get_meter"):
        from agentic_fleet.utils.tracing import get_meter, get_tracer, initialize_tracing

        if name == "initialize_tracing":
            return initialize_tracing
        if name == "get_tracer":
            return get_tracer
        return get_meter

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
