"""Package Search tool integration via MCP (Model Context Protocol)."""

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
                self.name = kwargs.get("name", "package_search")
                self.description = kwargs.get("description", "")


from agentic_fleet.utils.telemetry import optional_span

logger = logging.getLogger(__name__)


class PackageSearchMCPTool(MCPStreamableHTTPTool):
    """
    Package search tool using MCP protocol.
    """

    def __init__(self, mcp_url: str | None = None):
        """
        Initialize Package Search MCP tool.

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

        self.name = "package_search"
        self.description = description
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._resolved_tool_name: str | None = None

    async def run(self, query: str) -> str:
        """Run the package search tool."""
        with optional_span("PackageSearchMCPTool.run", attributes={"query": query}):
            try:
                await self._ensure_connection()
                tool_name = self._resolve_remote_tool_name()
                # Assuming the remote tool takes 'query' as argument.
                # If the MCP server exposes multiple tools, we might need logic to pick one.
                # For now, we assume the main tool is what we want.
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
                # Heuristic: pick the first one or one that matches 'search'
                if "search" in func.name.lower():
                    self._resolved_tool_name = func.name
                    return func.name
            # Fallback to first
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
        # Reuse the formatting logic from TavilyMCPTool or similar
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
