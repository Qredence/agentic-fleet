"""Base class for MCP (Model Context Protocol) tool integrations.

Provides common functionality for MCP-based tools including connection management,
tool resolution, and content formatting. Subclasses should override specific
behavior as needed while benefiting from shared infrastructure.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_framework._mcp import MCPStreamableHTTPTool
else:
    try:
        from agent_framework._mcp import MCPStreamableHTTPTool
    except (ImportError, ModuleNotFoundError, AttributeError):

        class MCPStreamableHTTPTool:
            """Fallback MCPStreamableHTTPTool for test environments."""

            def __init__(self, *args: Any, **kwargs: Any):
                self.name = kwargs.get("name", "mcp_tool")
                self.description = kwargs.get("description", "")


logger = logging.getLogger(__name__)


class BaseMCPTool(MCPStreamableHTTPTool):
    """Base class for MCP-based tools with shared connection and formatting logic.

    Provides common infrastructure for:
    - Connection management with thread-safe locking
    - Remote tool name resolution
    - Safe disconnection handling
    - Content formatting from MCP responses

    Subclasses must implement the `run` method and configure tool-specific
    parameters in their `__init__` method.
    """

    def __init__(
        self,
        name: str,
        url: str,
        description: str,
        load_tools: bool = True,
        load_prompts: bool = False,
    ):
        """Initialize the base MCP tool.

        Args:
            name: The tool name for identification
            url: The MCP server URL to connect to
            description: Human-readable description of the tool's purpose
            load_tools: Whether to load tools from the MCP server
            load_prompts: Whether to load prompts from the MCP server
        """
        super().__init__(
            name=name,
            url=url,
            description=description,
            load_tools=load_tools,
            load_prompts=load_prompts,
        )

        # Ensure downstream consumers can rely on explicit attributes
        self.name = name
        self.description = description

        # Internal helpers for ensuring one-time connection + cached tool name
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._resolved_tool_name: str | None = None

    @abstractmethod
    async def run(self, query: str, **kwargs: Any) -> str:
        """Execute the tool with the given query.

        Args:
            query: The query string to process
            **kwargs: Additional tool-specific arguments

        Returns:
            A formatted string result from the tool execution
        """
        pass

    async def _ensure_connection(self) -> None:
        """Ensure the MCP session is connected before invoking a tool.

        Uses double-checked locking pattern for thread safety while minimizing
        lock contention in the common case where connection is already established.
        """
        if getattr(self, "session", None) and getattr(self, "is_connected", False):
            return

        async with self._connect_lock:
            # Double-check after acquiring lock
            if getattr(self, "session", None) and getattr(self, "is_connected", False):
                return
            await self.connect()

    def _resolve_remote_tool_name(self, preferred_keywords: Sequence[str] | None = None) -> str:
        """Pick the actual tool name exposed by the MCP server.

        Uses a heuristic to find a suitable tool name from the available functions.
        The resolution is cached after the first successful lookup.

        Args:
            preferred_keywords: Optional list of keywords to prefer when matching
                tool names (e.g., ["search", "query", "get"]). If None, defaults
                to common search-related keywords.

        Returns:
            The resolved tool name to use for invocation
        """
        if self._resolved_tool_name:
            return self._resolved_tool_name

        keywords = preferred_keywords or ["search", "query", "get", "read"]
        functions = getattr(self, "functions", None)

        if functions:
            # First pass: look for tools matching preferred keywords
            for func in functions:
                remote_name = getattr(func, "name", None)
                if remote_name and any(k in remote_name.lower() for k in keywords):
                    self._resolved_tool_name = remote_name
                    return remote_name

            # Second pass: use first available function
            if len(functions) > 0:
                first_func = functions[0]
                remote_name = getattr(first_func, "name", None)
                if remote_name:
                    self._resolved_tool_name = remote_name
                    return remote_name

        # Fallback to the local name passed to the constructor
        self._resolved_tool_name = self.name
        return self._resolved_tool_name

    async def _safe_disconnect(self) -> None:
        """Safely disconnect MCP session with proper error handling.

        This method handles cleanup gracefully, logging but not raising
        exceptions if the disconnect fails (e.g., connection already closed).
        """
        try:
            if (
                hasattr(self, "session")
                and getattr(self, "is_connected", False)
                and hasattr(self, "disconnect")
            ):
                await self.disconnect()  # type: ignore[attr-defined]
        except Exception as e:
            # Log but don't raise - cleanup is best effort
            logger.debug(f"Error during MCP disconnect: {e}")

    @staticmethod
    def _format_contents(contents: Sequence[Any]) -> str:
        """Convert MCP content objects into a readable text block.

        Handles various content formats including objects with text/content
        attributes, dictionaries, and fallback to string conversion.

        Args:
            contents: Sequence of content objects from MCP response

        Returns:
            Formatted string with content blocks separated by double newlines
        """
        if not contents:
            return ""

        formatted: list[str] = []
        for item in contents:
            text_fragment: str | None = None

            # Prefer native text attributes
            if hasattr(item, "text"):
                text_value = item.text
                if text_value:
                    text_fragment = str(text_value)
            elif hasattr(item, "content"):
                content_value = item.content
                if content_value:
                    text_fragment = str(content_value)
            else:
                # Try to extract from dict representation
                try:
                    payload = item.to_dict()
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
