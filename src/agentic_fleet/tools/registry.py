"""Tool registry for mapping tool names to tool instances."""

from __future__ import annotations

import logging
from typing import Any

try:
    from agent_framework import HostedCodeInterpreterTool
except ImportError as e:
    raise ImportError(
        "agent-framework package is required. Install with: uv add agent-framework"
    ) from e

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for mapping tool names to tool instances."""

    def __init__(self) -> None:
        """Initialize tool registry with default tools."""
        self._tools: dict[str, Any] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register default tools available in the agent framework."""
        try:
            self._tools["HostedCodeInterpreterTool"] = HostedCodeInterpreterTool()
            logger.debug("Registered HostedCodeInterpreterTool")
        except Exception as e:
            logger.warning(f"Failed to register HostedCodeInterpreterTool: {e}")

    def register_tool(self, name: str, tool: Any) -> None:
        """Register a tool instance.

        Args:
            name: Tool name identifier
            tool: Tool instance
        """
        self._tools[name] = tool
        logger.debug(f"Registered tool: {name}")

    def get_tool(self, name: str) -> Any | None:
        """Get a tool instance by name.

        Args:
            name: Tool name identifier

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())
