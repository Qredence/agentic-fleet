"""Tavily web search tool integration for agent-framework.

Adds lightweight type information for the third-party ``tavily`` package which
currently lacks distributed type stubs (py.typed), preventing strict type
checking tools (e.g. mypy) from analyzing it. We provide minimal TypedDict
definitions and a ``TYPE_CHECKING`` stub for ``TavilyClient`` so that static
analysis succeeds without altering runtime behavior.
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Any, TypedDict

from agent_framework import ToolProtocol

from agentic_fleet.tools.serialization import SerializationMixin

try:  # pragma: no cover - optional dependency
    from tavily import TavilyClient  # type: ignore[import]
except (ImportError, ModuleNotFoundError):

    class TavilyClient:  # type: ignore[no-redef]
        """Fallback client used in CI where tavily-python isn't installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.api_key = kwargs.get("api_key")

        def search(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            query = kwargs.get("query", "")
            return {
                "results": [
                    {
                        "title": "Stubbed Tavily Result",
                        "url": "https://example.com",
                        "content": f"No real Tavily data available for '{query}'.",
                    }
                ],
                "answer": "Stubbed Tavily response",
            }


if TYPE_CHECKING:

    class TavilyResult(TypedDict, total=False):
        title: str
        url: str
        content: str

    class TavilySearchResponse(TypedDict, total=False):
        results: list[TavilyResult]
        answer: str


class TavilySearchTool(ToolProtocol, SerializationMixin):
    """Web search tool using the Tavily API."""

    def __init__(self, api_key: str | None = None, max_results: int = 5):
        """
        Initialize Tavily search tool.

        Args:
            api_key: Tavily API key (defaults to TAVILY_API_KEY env var)
            max_results: Maximum number of search results to return
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY must be set in environment or passed to constructor")

        # TavilyClient constructor accepts 'api_key' kwarg
        self.client = TavilyClient(api_key=self.api_key)  # type: ignore[call-arg]
        self.max_results = max_results
        # Primary runtime name retained for backward compatibility; registry will
        # add alias 'TavilySearchTool'.
        self.name: str = "tavily_search"
        self.description = (
            "MANDATORY: Use this tool for ANY query about events, dates, or information from 2024 onwards. "
            "Search the web for real-time information using Tavily. Provides accurate, up-to-date results with source citations. "
            "ALWAYS use this tool when asked about recent events, current data, elections, news, or anything requiring current information. "
            "Never rely on training data for time-sensitive queries."
        )
        self.additional_properties: dict[str, Any] | None = None

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to look up on the web",
                        },
                        "search_depth": {
                            "type": "string",
                            "enum": ["basic", "advanced"],
                            "description": "Search depth: 'basic' for quick results, 'advanced' for comprehensive search",
                            "default": "basic",
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    async def run(self, query: str, search_depth: str = "basic") -> str:
        """
        Execute a web search using Tavily.

        Args:
            query: The search query
            search_depth: 'basic' or 'advanced' search depth

        Returns:
            Formatted search results with sources
        """
        try:
            normalized_depth = search_depth if search_depth in {"basic", "advanced"} else "basic"

            # Perform search on a worker thread. Response is expected to be a mapping with optional
            # 'results' list and 'answer' summary. Use loose typing to remain
            # compatible if the API adds fields.
            response: dict[str, Any] = await asyncio.to_thread(
                self.client.search,  # type: ignore[attr-defined]
                query=query,
                search_depth=normalized_depth,  # type: ignore[arg-type]
                max_results=self.max_results,
            )

            # Format results
            if not response.get("results"):
                return f"No results found for query: {query}"

            formatted_results = [f"Search results for: {query}\n"]

            for idx, result in enumerate(response["results"], 1):
                title = result.get("title", "No title")
                url = result.get("url", "")
                content = result.get("content", "No content available")

                formatted_results.append(f"\n{idx}. {title}\n   Source: {url}\n   {content}\n")

            # Add answer if available
            if answer := response.get("answer"):
                formatted_results.insert(1, f"\nSummary: {answer}\n")

            return "".join(formatted_results)

        except Exception as e:
            return f"Error performing search: {e}"

    def __str__(self) -> str:
        return self.name

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """Convert tool to dictionary format for agent-framework.

        Returns the OpenAI function calling schema format.
        """
        return self.schema
