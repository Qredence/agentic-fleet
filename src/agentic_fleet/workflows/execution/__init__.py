"""Execution strategy modules for workflow execution."""

from __future__ import annotations

from agent_framework import ChatMessage, MagenticAgentMessageEvent, Role, WorkflowOutputEvent

from .delegated import execute_delegated, execute_delegated_streaming
from .parallel import execute_parallel, execute_parallel_streaming
from .sequential import (
    execute_sequential,
    execute_sequential_streaming,
    execute_sequential_with_handoffs,
)

__all__ = [
    "execute_delegated",
    "execute_delegated_streaming",
    "execute_parallel",
    "execute_parallel_streaming",
    "execute_sequential",
    "execute_sequential_streaming",
    "execute_sequential_with_handoffs",
]
