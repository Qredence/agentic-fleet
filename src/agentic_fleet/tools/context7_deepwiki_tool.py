"""Context7 DeepWiki tool integration via MCP (Model Context Protocol)."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_framework import MCPStreamableHTTPTool
else:
    try:
        from agent_framework import MCPStreamableHTTPTool
    except (ImportError, ModuleNotFoundError, AttributeError):

        class MCPStreamableHTTPTool:
            """Stub for MCPStreamableHTTPTool when agent_framework is missing."""

            def __init__(self, *args: Any, **kwargs: Any):
                self.name = kwargs.get("name", "context7_deepwiki")
                self.description = kwargs.get("description", "")


from agentic_fleet.utils.telemetry import optional_span

logger = logging.getLogger(__name__)


class Context7DeepWikiTool(MCPStreamableHTTPTool):
    """
    Context7 DeepWiki tool using MCP protocol.
    """

    def __init__(self, mcp_url: str | None = None):
        """
        Initialize Context7 DeepWiki MCP tool.

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

        self.name = "context7_deepwiki"
        self.description = description
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._resolved_tool_name: str | None = None

    async def run(self, query: str) -> str:
        """Run the DeepWiki tool."""
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

    async def _ensure_connection(self) -> None:
        if getattr(self, "session", None) and getattr(self, "is_connected", False):
            return
        async with self._connect_lock:
            if getattr(self, "session", None) and getattr(self, "is_connected", False):
                return
            await self.connect()

    def _resolve_remote_tool_name(self) -> str:
        if self._resolved_tool_name:
            return self._resolved_tool_name
        functions = getattr(self, "functions", None)
        if functions:
            for func in functions:
                # Heuristic: pick one that looks like 'search' or 'query' or 'get'
                if any(k in func.name.lower() for k in ["search", "query", "get", "read"]):
                    self._resolved_tool_name = func.name
                    return func.name
            if len(functions) > 0:
                self._resolved_tool_name = functions[0].name
                return functions[0].name

        self._resolved_tool_name = self.name
        return self._resolved_tool_name

    async def _safe_disconnect(self) -> None:
        try:
            if hasattr(self, "session") and getattr(self, "is_connected", False):
                disconnect_fn = getattr(self, "disconnect", None)
                if callable(disconnect_fn):
                    await disconnect_fn()
        except Exception:
            # Silently ignore cleanup errors - connection may already be closed
            # or session may have been invalidated by external factors
            pass

    @staticmethod
    def _format_contents(contents: Sequence[Any]) -> str:
        if not contents:
            return ""
        formatted = []
        for item in contents:
            text = None
            if hasattr(item, "text") and item.text:
                text = str(item.text)
            elif hasattr(item, "content") and item.content:
                text = str(item.content)
            else:
                text = str(item)
            if text:
                formatted.append(text)
        return "\n\n".join(formatted)
