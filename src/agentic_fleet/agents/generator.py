"""Generator agent implementation."""

from __future__ import annotations

from typing import Any


def get_config() -> dict[str, Any]:
    """Get generator agent configuration.

    Returns:
        Generator agent configuration dictionary
    """
    return {
        "model": "gpt-5-mini",
        "instructions": "prompts.generator",
        "description": "Synthesizes verified work into the final answer",
        "reasoning": {
            "effort": "low",
            "verbosity": "verbose",
        },
        "temperature": 0.8,
        "max_tokens": 6144,
        "store": True,
    }


__all__ = ["get_config"]
