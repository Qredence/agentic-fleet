"""Adapter wrapping HostedCodeInterpreterTool to provide a stable function-style schema.

This avoids parse warnings from the external agent_framework tool parser by guaranteeing
an OpenAI function calling compatible schema and a predictable tool name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework import HostedCodeInterpreterTool, ToolProtocol

# Import SerializationMixin with fallback while keeping static analysis happy
if TYPE_CHECKING:  # pragma: no cover - typing helper
    from agent_framework._serialization import SerializationMixin
else:
    try:
        from agent_framework._serialization import SerializationMixin
    except (ImportError, ModuleNotFoundError, AttributeError):  # pragma: no cover - optional dep

        class SerializationMixin:  # type: ignore[too-many-ancestors]
            """Fallback SerializationMixin for environments where agent_framework._serialization is not available."""

            def to_dict(self, **_: Any) -> dict[str, Any]:
                return {}


class HostedCodeInterpreterAdapter(ToolProtocol, SerializationMixin):
    """Adapter that standardizes the HostedCodeInterpreterTool interface."""

    def __init__(self, underlying: HostedCodeInterpreterTool | None = None):
        self._underlying = underlying or HostedCodeInterpreterTool()
        # Canonical name (PascalCase) for consistency with config/tests
        self.name = "HostedCodeInterpreterTool"
        self.description = (
            "Execute Python code snippets in an isolated sandbox environment for analysis, "
            "data transformation, and quick computation."
        )
        self.additional_properties: dict[str, Any] | None = {}

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute in the sandbox",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Optional execution timeout in seconds",
                            "default": 30,
                        },
                    },
                    "required": ["code"],
                },
            },
        }

    def __str__(self) -> str:
        return self.name

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """Convert tool to dictionary format for agent-framework.

        Returns the OpenAI function calling schema format.
        """
        return self.schema
