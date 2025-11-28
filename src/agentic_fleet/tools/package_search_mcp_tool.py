"""Package Search tool integration via MCP (Model Context Protocol)."""

from __future__ import annotations

import logging
import os
from typing import Any

from agentic_fleet.utils.telemetry import optional_span

from .base_mcp_tool import BaseMCPTool

logger = logging.getLogger(__name__)


class PackageSearchMCPTool(BaseMCPTool):
    """Package search tool using MCP protocol."""

    def __init__(self, mcp_url: str | None = None):
        """Initialize Package Search MCP tool.

        Args:
            mcp_url: URL of the Package Search MCP server (defaults to PACKAGE_SEARCH_MCP_URL env var)
        """
        mcp_url = mcp_url or os.getenv("PACKAGE_SEARCH_MCP_URL")
        if not mcp_url:
            raise ValueError(
                "PACKAGE_SEARCH_MCP_URL must be set in environment or passed to constructor"
            )

        description = (
            "Search for software packages, libraries, and their documentation. "
            "Use this tool to find relevant packages for a given task or codebase."
        )

        super().__init__(
            name="package_search",
            url=mcp_url,
            description=description,
            load_tools=True,
            load_prompts=False,
        )

    async def run(self, query: str, **kwargs: Any) -> str:
        """Run the package search tool.

        Args:
            query: The search query to process
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted string result from package search or an error message
        """
        with optional_span("PackageSearchMCPTool.run", attributes={"query": query}):
            try:
                await self._ensure_connection()
                tool_name = self._resolve_remote_tool_name(preferred_keywords=["search"])
                contents = await self.call_tool(tool_name, query=query)
                result = (
                    self._format_contents(contents) or "Package search returned empty response."
                )
                await self._safe_disconnect()
                return result
            except Exception as exc:
                logger.warning("Package Search MCP tool call failed: %s", exc)
                await self._safe_disconnect()
                return f"Error: Package Search failed. {exc}"
