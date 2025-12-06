"""MCP (Model Context Protocol) tool integrations.

Consolidated MCP tool implementations:
- TavilyMCPTool: Web search via Tavily API
- Context7DeepWikiTool: Deep contextual information
- PackageSearchMCPTool: Software package search

All tools extend BaseMCPTool from base_mcp_tool.py.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from agent_framework.exceptions import ToolException, ToolExecutionException

from .base_mcp_tool import BaseMCPTool

logger = logging.getLogger(__name__)


# =============================================================================
# Tavily MCP Tool
# =============================================================================


class TavilyMCPTool(BaseMCPTool):
    """Web search tool using Tavily API via MCP protocol.

    This tool connects to Tavily's MCP server and automatically loads
    available tools from the server. It provides better integration
    with agent-framework's ChatAgent compared to direct API integration.

    Authentication:
        The API key is passed via HTTP Authorization header (Bearer token)
        rather than URL query parameters. This is the preferred authentication
        method as it prevents credentials from appearing in logs or URL history.

        Both methods are supported by the Tavily MCP server:
        - Authorization header (used here): ``Authorization: Bearer <api_key>``
        - URL query parameter (legacy): ``?tavilyApiKey=<api_key>``

    Note:
        If migrating from an older implementation that used URL query parameters,
        no client-side changes are required. The Authorization header method is
        fully compatible with the Tavily MCP server.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Tavily MCP tool.

        Args:
            api_key: Tavily API key (defaults to TAVILY_API_KEY env var)

        Raises:
            ValueError: If API key is not provided
        """
        api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY must be set in environment or passed to constructor")

        mcp_url = "https://mcp.tavily.com/mcp/"

        # Pass API key via header to avoid leaking credentials in URLs/logs
        auth_headers = {"Authorization": f"Bearer {api_key}"}

        description = (
            "MANDATORY: Use this tool for ANY query about events, dates, or information from 2024 onwards. "
            "Search the web for real-time information using Tavily. Provides accurate, up-to-date results with source citations. "
            "ALWAYS use this tool when asked about recent events, current data, elections, news, or anything requiring current information. "
            "Never rely on training data for time-sensitive queries."
        )

        super().__init__(
            name="tavily_search",
            url=mcp_url,
            description=description,
            load_tools=True,
            load_prompts=False,
            headers=auth_headers,
        )

        logger.info("Initialized TavilyMCPTool successfully")

    async def run(self, query: str, **kwargs: Any) -> str:
        """Execute a Tavily search query via MCP.

        Args:
            query: Tavily search query from the agent
            **kwargs: Additional arguments. Supports 'search_depth' ("basic" or "advanced")

        Returns:
            Human-readable string with Tavily results or an error message.
        """
        search_depth = kwargs.get("search_depth", "basic")
        normalized_depth = search_depth if search_depth in {"basic", "advanced"} else "basic"

        try:
            await self._ensure_connection()
            tool_name = self._resolve_remote_tool_name()
            contents = await self.call_tool(tool_name, query=query, search_depth=normalized_depth)
            result = self._format_contents(contents) or "Tavily returned an empty response."
            await self._safe_disconnect()
            return result
        except (ToolExecutionException, ToolException) as exc:
            logger.warning("Tavily MCP tool call failed: %s", exc)
            await self._safe_disconnect()
            return (
                "Error: Tavily MCP search failed to execute. "
                "Verify your TAVILY_API_KEY and network connectivity."
            )
        except Exception as exc:  # pragma: no cover - unexpected
            logger.exception("Unexpected Tavily MCP failure", exc_info=exc)
            await self._safe_disconnect()
            return f"Unexpected Tavily MCP error: {exc}"


# =============================================================================
# Context7 DeepWiki Tool
# =============================================================================


class Context7DeepWikiTool(BaseMCPTool):
    """Context7 DeepWiki tool using MCP protocol."""

    def __init__(self, mcp_url: str | None = None):
        """Initialize Context7 DeepWiki MCP tool.

        Args:
            mcp_url: URL of the Context7 DeepWiki MCP server (defaults to CONTEXT7_DEEPWIKI_MCP_URL env var)
        """
        from ..utils.telemetry import optional_span  # Avoid circular import at module level

        self._optional_span = optional_span

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
        with self._optional_span("Context7DeepWikiTool.run", attributes={"query": query}):
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


# =============================================================================
# Package Search Tool
# =============================================================================


class PackageSearchMCPTool(BaseMCPTool):
    """Package search tool using MCP protocol."""

    def __init__(self, mcp_url: str | None = None):
        """Initialize Package Search MCP tool.

        Args:
            mcp_url: URL of the Package Search MCP server (defaults to PACKAGE_SEARCH_MCP_URL env var)
        """
        from ..utils.telemetry import optional_span  # Avoid circular import at module level

        self._optional_span = optional_span

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
        with self._optional_span("PackageSearchMCPTool.run", attributes={"query": query}):
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
