"""Core module for AgenticFleet.

This package provides core infrastructure components:
- config: Configuration management (settings, workflow config, env vars)
- logging: Logging, tracing, telemetry, and resilience utilities
- storage: Persistence (conversations, history, caching)
- middleware: Chat workflow middleware (history bridging, converters)

Usage:
    from agentic_fleet.core import get_settings, setup_logger, ConversationStore

    # Or import from submodules for full access
    from agentic_fleet.core.config import load_workflow_config, env_config
    from agentic_fleet.core.logging import initialize_tracing, optional_span
    from agentic_fleet.core.storage import HistoryManager, TTLCache
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Lazy imports for commonly used items
if TYPE_CHECKING:
    from agentic_fleet.core.config import AppSettings, env_config, get_settings, load_config
    from agentic_fleet.core.logging import (
        initialize_tracing,
        optional_span,
        setup_logger,
    )
    from agentic_fleet.core.middleware import (
        BridgeConverter,
        BridgeMiddleware,
        ChatMiddleware,
    )
    from agentic_fleet.core.storage import ConversationStore, HistoryManager, TTLCache

__all__ = [
    # Config
    "AppSettings",
    # Middleware
    "BridgeConverter",
    "BridgeMiddleware",
    "ChatMiddleware",
    # Storage
    "ConversationStore",
    "HistoryManager",
    "TTLCache",
    "env_config",
    "get_settings",
    "initialize_tracing",
    "load_config",
    "optional_span",
    # Logging
    "setup_logger",
]


def __getattr__(name: str) -> object:
    """Lazy import for public API."""
    if name in ("ChatMiddleware", "BridgeMiddleware", "BridgeConverter"):
        from agentic_fleet.core.middleware import (
            BridgeConverter,
            BridgeMiddleware,
            ChatMiddleware,
        )

        return {
            "ChatMiddleware": ChatMiddleware,
            "BridgeMiddleware": BridgeMiddleware,
            "BridgeConverter": BridgeConverter,
        }[name]

    if name in ("AppSettings", "get_settings", "env_config", "load_config"):
        from agentic_fleet.core.config import AppSettings, env_config, get_settings, load_config

        return {
            "AppSettings": AppSettings,
            "get_settings": get_settings,
            "env_config": env_config,
            "load_config": load_config,
        }[name]

    if name in ("setup_logger", "initialize_tracing", "optional_span"):
        from agentic_fleet.core.logging import (
            initialize_tracing,
            optional_span,
            setup_logger,
        )

        return {
            "setup_logger": setup_logger,
            "initialize_tracing": initialize_tracing,
            "optional_span": optional_span,
        }[name]

    if name in ("ConversationStore", "HistoryManager", "TTLCache"):
        from agentic_fleet.core.storage import ConversationStore, HistoryManager, TTLCache

        return {
            "ConversationStore": ConversationStore,
            "HistoryManager": HistoryManager,
            "TTLCache": TTLCache,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
