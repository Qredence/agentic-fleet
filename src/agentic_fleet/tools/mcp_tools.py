"""MCP (Model Context Protocol) tool integration."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """Registry for MCP (Model Context Protocol) tools."""

    def __init__(self) -> None:
        """Initialize MCP tool registry."""
        self._tools: dict[str, Any] = {}

    def register_mcp_tool(self, name: str, tool: Any) -> None:
        """Register an MCP tool instance.

        Args:
            name: Tool name identifier
            tool: MCP tool instance
        """
        self._tools[name] = tool
        logger.debug(f"Registered MCP tool: {name}")

    def get_mcp_tool(self, name: str) -> Any | None:
        """Get an MCP tool instance by name.

        Args:
            name: Tool name identifier

        Returns:
            MCP tool instance or None if not found
        """
        return self._tools.get(name)

    def list_mcp_tools(self) -> list[str]:
        """List all registered MCP tool names.

        Returns:
            List of MCP tool names
        """
        return list(self._tools.keys())
