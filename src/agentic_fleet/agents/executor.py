"""Executor agent implementation."""

from __future__ import annotations

from typing import Any


def get_config() -> dict[str, Any]:
    """Get executor agent configuration.

    Returns:
        Executor agent configuration dictionary
    """
    return {
        "model": "gpt-5-mini",
        "instructions": "prompts.executor",
        "description": "Executes active plan steps and coordinates other specialists",
        "reasoning": {
            "effort": "medium",
            "verbosity": "verbose",
        },
        "temperature": 0.6,
        "max_tokens": 4096,
        "store": True,
    }


__all__ = ["get_config"]
