"""Utilities package: compiler, config loader, logging, tracing, and tool registry.

This package provides utility functions and classes used throughout agentic_fleet,
including configuration management, DSPy compilation, caching, logging, tracing,
and tool registry functionality.

Submodules (organized by domain):
    - utils.cfg: Configuration, schemas, models, types, constants (organized re-exports)
    - utils.infra: Telemetry, tracing, resilience, logging (organized re-exports)
    - utils.storage: Cosmos DB, persistence, history, job stores (organized re-exports)

Public API (backward-compatible):
    - ToolRegistry: Central registry for managing tool metadata
    - ToolMetadata: Metadata class for registered tools
    - TTLCache: In-memory cache with TTL support
    - compile_reasoner: Function to compile DSPy supervisor modules
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
    from agentic_fleet.utils.cfg import (
        env_config,
        get_agent_model,
        get_config_path,
        load_config,
        validate_agentic_fleet_env,
    )
    from agentic_fleet.utils.compiler import compile_reasoner
    from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
    from agentic_fleet.utils.profiling import (
        PerformanceTracker,
        get_performance_stats,
        log_performance_summary,
        profile_function,
        reset_performance_stats,
        timed_operation,
        track_operation,
    )
    from agentic_fleet.utils.tool_registry import ToolMetadata, ToolRegistry
    from agentic_fleet.utils.tracing import get_meter, get_tracer, initialize_tracing

__all__ = [
    "ExecutionMode",
    "PerformanceTracker",
    "RoutingDecision",
    "TTLCache",
    "ToolMetadata",
    "ToolRegistry",
    "compile_reasoner",
    "env_config",
    "get_agent_model",
    "get_config_path",
    "get_meter",
    "get_performance_stats",
    "get_tracer",
    "initialize_tracing",
    "load_config",
    "log_performance_summary",
    "profile_function",
    "reset_performance_stats",
    "timed_operation",
    "track_operation",
    "validate_agentic_fleet_env",
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

    if name in (
        "load_config",
        "get_agent_model",
        "get_config_path",
        "env_config",
        "validate_agentic_fleet_env",
    ):
        from agentic_fleet.utils.cfg import (
            env_config,
            get_agent_model,
            get_config_path,
            load_config,
            validate_agentic_fleet_env,
        )

        return {
            "load_config": load_config,
            "get_config_path": get_config_path,
            "get_agent_model": get_agent_model,
            "env_config": env_config,
            "validate_agentic_fleet_env": validate_agentic_fleet_env,
        }[name]

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

    if name in (
        "timed_operation",
        "profile_function",
        "PerformanceTracker",
        "track_operation",
        "get_performance_stats",
        "log_performance_summary",
        "reset_performance_stats",
    ):
        from agentic_fleet.utils.profiling import (
            PerformanceTracker,
            get_performance_stats,
            log_performance_summary,
            profile_function,
            reset_performance_stats,
            timed_operation,
            track_operation,
        )

        return {
            "timed_operation": timed_operation,
            "profile_function": profile_function,
            "PerformanceTracker": PerformanceTracker,
            "track_operation": track_operation,
            "get_performance_stats": get_performance_stats,
            "log_performance_summary": log_performance_summary,
            "reset_performance_stats": reset_performance_stats,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
