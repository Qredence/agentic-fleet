"""Base classes and mixins for AgenticFleet tools.

Provides common functionality for tool implementations that integrate with
the agent-framework ecosystem.
"""

from __future__ import annotations

from typing import Any


class SchemaToolMixin:
    """Mixin providing common tool interface methods.

    This mixin provides the `to_dict` method that converts tools to the
    OpenAI function calling schema format expected by agent-framework.

    Classes using this mixin must have a `schema` property that returns
    the tool's schema dict.

    Example:
        class MyTool(ToolProtocol, SerializationMixin, SchemaToolMixin):
            @property
            def schema(self) -> dict[str, Any]:
                return {"type": "function", "function": {...}}

            # to_dict is now inherited from SchemaToolMixin
    """

    # Type hint for the expected schema property (implemented by subclasses)
    schema: dict[str, Any]

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """Convert tool to dictionary format for agent-framework.

        Returns the OpenAI function calling schema format.

        Args:
            **kwargs: Additional keyword arguments (ignored, for compatibility).

        Returns:
            The tool's schema dictionary.
        """
        return self.schema
