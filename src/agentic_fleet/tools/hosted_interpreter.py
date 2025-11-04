"""Hosted code interpreter tool integration."""

from __future__ import annotations

from typing import Any

try:
    from agent_framework import HostedCodeInterpreterTool
except ImportError as e:
    raise ImportError(
        "agent-framework package is required. Install with: uv add agent-framework"
    ) from e

__all__ = ["HostedCodeInterpreterTool"]
