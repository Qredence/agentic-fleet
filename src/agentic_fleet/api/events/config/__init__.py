"""UI routing configuration loading and parsing."""

from __future__ import annotations

from .routing_config import (
    UIRoutingConfig,
    UIRoutingEntry,
    UIRoutingEventConfig,
    classify_event,
    load_ui_routing_config,
)

__all__ = [
    "UIRoutingConfig",
    "UIRoutingEntry",
    "UIRoutingEventConfig",
    "classify_event",
    "load_ui_routing_config",
]
