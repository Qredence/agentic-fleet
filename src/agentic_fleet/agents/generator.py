"""Generator agent implementation."""

from __future__ import annotations

import os
from typing import Any


def get_config() -> dict[str, Any]:
    """Get generator agent configuration.

    Returns:
        Generator agent configuration dictionary
    """
    return {
        "model": os.getenv("FAST_PATH_MODEL", "gpt-5-mini"),
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
