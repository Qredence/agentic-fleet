"""Adapter wrapping HostedCodeInterpreterTool to provide a stable function-style schema.

This avoids parse warnings from the external agent_framework tool parser by guaranteeing
an OpenAI function calling compatible schema and a predictable tool name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from agent_framework._serialization import SerializationMixin
from agent_framework._tools import HostedCodeInterpreterTool

from agentic_fleet.tools.base import SchemaToolMixin

if TYPE_CHECKING:  # pragma: no cover - typing helper

    class ToolProtocolBase(Protocol):
        """Protocol describing the methods expected by agent_framework tools."""

        name: str
        description: str

        @property
        def schema(self) -> dict[str, Any]:
            """Return the tool schema."""
            ...

        def to_dict(self, **kwargs: Any) -> dict[str, Any]:
            """Convert tool to dictionary format."""
            ...

else:
    from agent_framework._tools import ToolProtocol as ToolProtocolBase


class HostedCodeInterpreterAdapter(SchemaToolMixin, ToolProtocolBase, SerializationMixin):
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
        """Return the tool schema."""
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

    # to_dict inherited from SchemaToolMixin
