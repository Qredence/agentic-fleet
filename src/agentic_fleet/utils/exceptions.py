"""
Shared exception classes for the AgenticFleet package.

This module provides common exception types that are used across different
layers of the application to avoid circular dependencies between modules.
"""

from __future__ import annotations

from typing import Any


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing.

    This is a shared exception type used across the application to avoid
    circular dependencies between utils and workflows modules.
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_value: Any = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize configuration error.

        Args:
            message: Error message
            config_key: The configuration key that caused the error
            config_value: The invalid configuration value
            context: Optional additional context
        """
        super().__init__(message)
        self.message = message
        self.config_key = config_key
        self.config_value = config_value
        self.context = context or {}

    def __str__(self) -> str:
        """Return formatted error message with context."""
        parts = [self.message]
        if self.config_key:
            parts.append(f"config_key={self.config_key}")
        if self.config_value is not None:
            parts.append(f"config_value={self.config_value}")
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(context_str)

        if len(parts) > 1:
            return f"{parts[0]} ({', '.join(parts[1:])})"
        return parts[0]


__all__ = ["ConfigurationError"]
