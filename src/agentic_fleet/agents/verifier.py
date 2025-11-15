"""Verifier agent implementation."""

from __future__ import annotations

import os
from typing import Any


def get_config() -> dict[str, Any]:
    """Get verifier agent configuration.

    Returns:
        Verifier agent configuration dictionary
    """
    return {
        "model": os.getenv("FAST_PATH_MODEL", "gpt-5-mini"),
        "instructions": "prompts.verifier",
        "description": "Validates intermediate outputs and flags quality issues",
        "reasoning": {
            "effort": "high",
            "verbosity": "verbose",
        },
        "temperature": 0.5,
        "max_tokens": 4096,
        "store": True,
    }


__all__ = ["get_config"]
