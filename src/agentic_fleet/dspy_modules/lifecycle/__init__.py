"""DSPy lifecycle management.

This package provides centralized DSPy language model management:
- LM instance creation and caching (singleton pattern)
- Azure/OpenAI backend support
- Configuration and settings management
"""

from __future__ import annotations

from .manager import (
    configure_dspy_settings,
    get_current_lm,
    get_dspy_lm,
    get_reflection_lm,
    reset_dspy_manager,
)

__all__ = [
    "configure_dspy_settings",
    "get_current_lm",
    "get_dspy_lm",
    "get_reflection_lm",
    "reset_dspy_manager",
]
