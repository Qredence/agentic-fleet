"""Coder agent implementation."""

from __future__ import annotations

from typing import Any


def get_config() -> dict[str, Any]:
    """Get coder agent configuration.

    Returns:
        Coder agent configuration dictionary
    """
    return {
        "model": "gpt-5-mini",
        "instructions": "prompts.coder",
        "description": "Writes and executes code to unblock the team",
        "reasoning": {
            "effort": "high",
            "verbosity": "verbose",
        },
        "temperature": 0.3,
        "max_tokens": 8192,
        "store": True,
        "tools": ["HostedCodeInterpreterTool"],
    }


__all__ = ["get_config"]
