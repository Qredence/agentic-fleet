"""Tavily web search tool integration via MCP (Model Context Protocol).

Uses agent-framework's MCPStreamableHTTPTool to connect to Tavily's MCP server,
providing better integration with agent-framework's ChatAgent and improved
tool invocation reliability.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from agent_framework.exceptions import ToolException, ToolExecutionException

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from agent_framework import MCPStreamableHTTPTool
else:
    try:
        from agent_framework import MCPStreamableHTTPTool
    except (ImportError, ModuleNotFoundError, AttributeError):  # pragma: no cover - optional dep

        class MCPStreamableHTTPTool:  # type: ignore[too-many-ancestors]
            """Fallback MCPStreamableHTTPTool for test environments."""

            def __init__(self, *args: Any, **kwargs: Any):
                self.name = kwargs.get("name", "tavily_search")
                self.description = kwargs.get("description", "")


logger = logging.getLogger(__name__)


class TavilyMCPTool(MCPStreamableHTTPTool):
    """
    Web search tool using Tavily API via MCP protocol.

    This tool connects to Tavily's MCP server and automatically loads
    available tools from the server. It provides better integration
    with agent-framework's ChatAgent compared to direct API integration.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize Tavily MCP tool.

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

        # Initialize MCPStreamableHTTPTool
        # The MCP server will provide the actual tool schemas, so we set load_tools=True
        # and load_prompts=False since we only need tools
        super().__init__(
            name="tavily_search",
            url=mcp_url,
            description=description,
            load_tools=True,
            load_prompts=False,
        )

        # Ensure downstream consumers can rely on explicit attributes even if the base class changes
        self.name = "tavily_search"
        self.description = description

        # Log initialization without exposing API key
        logger.info("Initialized TavilyMCPTool successfully")

        # Internal helpers for ensuring one-time connection + cached tool name
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._resolved_tool_name: str | None = None

    async def run(self, query: str, search_depth: str = "basic") -> str:
        """Adapter to mimic ToolProtocol.run for agent-framework ChatAgent.

        Args:
            query: Tavily search query from the agent
            search_depth: Optional Tavily depth ("basic" or "advanced")

        Returns:
            Human-readable string with Tavily results or an error message.
        """

        normalized_depth = search_depth if search_depth in {"basic", "advanced"} else "basic"

        try:
            await self._ensure_connection()
            tool_name = self._resolve_remote_tool_name()
            contents = await self.call_tool(tool_name, query=query, search_depth=normalized_depth)
            result = self._format_contents(contents) or "Tavily returned an empty response."
            # Ensure proper cleanup by disconnecting after use
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

    async def _ensure_connection(self) -> None:
        """Ensure the MCP session is connected before invoking a tool."""

        if getattr(self, "session", None) and getattr(self, "is_connected", False):
            return

        async with self._connect_lock:
            if getattr(self, "session", None) and getattr(
                self, "is_connected", False
            ):  # double-check
                return
            await self.connect()

    def _resolve_remote_tool_name(self) -> str:
        """Pick the actual tool name exposed by the MCP server."""

        if self._resolved_tool_name:
            return self._resolved_tool_name

        functions = getattr(self, "functions", None)
        if functions:
            for func in functions:
                remote_name = getattr(func, "name", None)
                if remote_name:
                    self._resolved_tool_name = remote_name
                    return remote_name

        # Fallback to the local name passed to the constructor
        self._resolved_tool_name = self.name
        return self._resolved_tool_name

    async def _safe_disconnect(self) -> None:
        """Safely disconnect MCP session with proper error handling."""
        try:
            if (
                hasattr(self, "session")
                and getattr(self, "is_connected", False)
                and hasattr(self, "disconnect")
            ):
                # Disconnect in same async context to avoid RuntimeError
                await self.disconnect()  # type: ignore[attr-defined]
        except Exception as e:
            # Log but don't raise - cleanup is best effort
            logger.debug(f"Error during MCP disconnect: {e}")

    @staticmethod
    def _format_contents(contents: Sequence[Any]) -> str:
        """Convert MCP content objects into a readable text block."""

        if not contents:
            return ""

        formatted: list[str] = []
        for item in contents:
            text_fragment: str | None = None

            # Prefer native text attributes
            if hasattr(item, "text"):
                text_value = item.text  # type: ignore[attr-defined]
                if text_value:
                    text_fragment = str(text_value)
            elif hasattr(item, "content"):
                content_value = item.content  # type: ignore[attr-defined]
                if content_value:
                    text_fragment = str(content_value)
            else:
                try:
                    payload = item.to_dict()  # type: ignore[call-arg]
                except Exception:
                    payload = None

                if isinstance(payload, dict):
                    if payload.get("text"):
                        text_fragment = str(payload["text"])
                    elif payload.get("content"):
                        text_fragment = str(payload["content"])
                    elif payload.get("error"):
                        text_fragment = f"Error: {payload['error']}"
                    elif payload.get("data"):
                        try:
                            text_fragment = json.dumps(
                                payload["data"], ensure_ascii=False, indent=2
                            )
                        except TypeError:
                            text_fragment = str(payload["data"])
                    else:
                        text_fragment = json.dumps(payload, ensure_ascii=False)
                else:
                    text_fragment = str(item)

            if text_fragment:
                formatted.append(text_fragment.strip())

        return "\n\n".join(fragment for fragment in formatted if fragment)
