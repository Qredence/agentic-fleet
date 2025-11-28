"""Context7 DeepWiki tool integration via MCP (Model Context Protocol)."""

from __future__ import annotations

import logging
import os
from typing import Any

from agentic_fleet.utils.telemetry import optional_span

from .base_mcp_tool import BaseMCPTool

logger = logging.getLogger(__name__)


class Context7DeepWikiTool(BaseMCPTool):
    """Context7 DeepWiki tool using MCP protocol."""

    def __init__(self, mcp_url: str | None = None):
        """Initialize Context7 DeepWiki MCP tool.

        Args:
            mcp_url: URL of the Context7 DeepWiki MCP server (defaults to CONTEXT7_DEEPWIKI_MCP_URL env var)
        """
        mcp_url = mcp_url or os.getenv("CONTEXT7_DEEPWIKI_MCP_URL")
        if not mcp_url:
            raise ValueError(
                "CONTEXT7_DEEPWIKI_MCP_URL must be set in environment or passed to constructor"
            )

        description = (
            "Access Context7 DeepWiki for deep contextual information and documentation. "
            "Use this tool to retrieve detailed knowledge about concepts, libraries, or systems."
        )

        super().__init__(
            name="context7_deepwiki",
            url=mcp_url,
            description=description,
            load_tools=True,
            load_prompts=False,
        )

    async def run(self, query: str, **kwargs: Any) -> str:
        """Run the DeepWiki tool.

        Args:
            query: The search query to process
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted string result from DeepWiki or an error message
        """
        with optional_span("Context7DeepWikiTool.run", attributes={"query": query}):
            try:
                await self._ensure_connection()
                tool_name = self._resolve_remote_tool_name()
                contents = await self.call_tool(tool_name, query=query)
                result = self._format_contents(contents) or "DeepWiki returned empty response."
                await self._safe_disconnect()
                return result
            except Exception as exc:
                logger.warning("Context7 DeepWiki MCP tool call failed: %s", exc)
                await self._safe_disconnect()
                return f"Error: DeepWiki search failed. {exc}"
