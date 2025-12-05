"""
Core utility surface for error handling, shared models, and typing protocols.

This module re-exports the most commonly used primitives so callers can import
from a single location without changing existing module paths.
"""

from __future__ import annotations

from .error_utils import (
    create_user_facing_error,
    log_error_with_context,
    sanitize_error_message,
    sanitize_task_content,
)
from .models import ExecutionMode, RoutingDecision, ensure_routing_decision
from .types import (
    CacheProtocol,
    ChatClient,
    ChatClientWithExtraBody,
    DSPyModule,
    DSPySettings,
    DSPySignature,
    ProgressCallback,
    ToolProtocol,
)

__all__ = [
    "CacheProtocol",
    "ChatClient",
    "ChatClientWithExtraBody",
    "DSPyModule",
    "DSPySettings",
    "DSPySignature",
    "ExecutionMode",
    "ProgressCallback",
    "RoutingDecision",
    "ToolProtocol",
    "create_user_facing_error",
    "ensure_routing_decision",
    "log_error_with_context",
    "sanitize_error_message",
    "sanitize_task_content",
]
