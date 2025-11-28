"""Tavily web search tool integration via MCP (Model Context Protocol).

Uses agent-framework's MCPStreamableHTTPTool to connect to Tavily's MCP server,
providing better integration with agent-framework's ChatAgent and improved
tool invocation reliability.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from agent_framework.exceptions import ToolException, ToolExecutionException

from .base_mcp_tool import BaseMCPTool

logger = logging.getLogger(__name__)


class TavilyMCPTool(BaseMCPTool):
    """Web search tool using Tavily API via MCP protocol.

    This tool connects to Tavily's MCP server and automatically loads
    available tools from the server. It provides better integration
    with agent-framework's ChatAgent compared to direct API integration.
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

        # Construct MCP URL with API key
        mcp_url = f"https://mcp.tavily.com/mcp/?tavilyApiKey={api_key}"

        # Enhanced description to emphasize mandatory usage for time-sensitive queries
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
        )

        # Log initialization without exposing API key
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
