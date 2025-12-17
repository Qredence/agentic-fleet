"""Tavily web search tool integration for agent-framework.

Adds lightweight type information for the third-party ``tavily`` package which
currently lacks distributed type stubs (py.typed), preventing strict type
checking tools (e.g. ty) from analyzing it. We provide minimal TypedDict
definitions and a ``TYPE_CHECKING`` stub for ``TavilyClient`` so that static
analysis succeeds without altering runtime behavior.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, TypedDict

from agent_framework._serialization import SerializationMixin
from agent_framework._tools import ToolProtocol

from agentic_fleet.tools.base import SchemaToolMixin
from agentic_fleet.utils.cfg import env_config
from agentic_fleet.utils.resilience import external_api_retry

try:  # Optional dependency — keep import non-fatal at module load time
    from tavily import TavilyClient  # type: ignore[import]

    _tavily_import_error: Exception | None = None
except (ImportError, ModuleNotFoundError) as exc:
    TavilyClient = None  # type: ignore[assignment]
    _tavily_import_error = exc


if TYPE_CHECKING:

    class TavilyResult(TypedDict, total=False):
        """Type definition for a single Tavily search result."""

        title: str
        url: str
        content: str

    class TavilySearchResponse(TypedDict, total=False):
        """Type definition for the Tavily search response."""

        results: list[TavilyResult]
        answer: str


class TavilySearchTool(SchemaToolMixin, ToolProtocol, SerializationMixin):
    """Web search tool using the Tavily API."""

    def __init__(self, api_key: str | None = None, max_results: int = 5):
        """
        Initialize Tavily search tool.

        Args:
            api_key: Tavily API key (defaults to TAVILY_API_KEY env var)
            max_results: Maximum number of search results to return
        """
        self.api_key = api_key or env_config.tavily_api_key
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY must be set in environment or passed to constructor")

        if TavilyClient is None:
            # Defer hard failure until instantiation so the package remains optional at import time
            raise ImportError(
                "The 'tavily-python' package is required to use TavilySearchTool. "
                "Install it with 'pip install tavily-python'."
            ) from _tavily_import_error

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
        """Return the tool schema."""
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
                            "default": "advanced",
                        },
                        "topic": {
                            "type": "string",
                            "enum": ["general", "news"],
                            "description": "Search topic: 'general' for broad search, 'news' for recent events",
                            "default": "general",
                        },
                        "include_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of domains to include in the search (e.g. ['wsj.com', 'reddit.com'])",
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    @external_api_retry
    async def run(self, query: str, **kwargs: Any) -> str:
        """Perform a web search via Tavily and return a formatted text summary.

        Parameters:
            query (str): Search query string.
            **kwargs: Optional search modifiers:
                search_depth (str): "basic" or "advanced"; defaults to "advanced".
                topic (str): "general" or "news"; defaults to "general".
                include_domains (list[str] | None): List of domains to restrict
                    results to; if omitted no domain filter is applied.

        Returns:
            str: A human-readable string containing a summary (if provided)
                followed by numbered search results with title, source URL, and
                content; or an error/no-results message.
        """
        try:
            search_depth = kwargs.get("search_depth", "advanced")
            topic = kwargs.get("topic", "general")
            include_domains = kwargs.get("include_domains")

            normalized_depth = search_depth if search_depth in {"basic", "advanced"} else "advanced"
            normalized_topic = topic if topic in {"general", "news"} else "general"

            # Perform search on a worker thread. Response is expected to be a mapping with optional
            # 'results' list and 'answer' summary. Use loose typing to remain
            # compatible if the API adds fields.
            search_kwargs: dict[str, Any] = {
                "query": query,
                "search_depth": normalized_depth,
                "max_results": self.max_results,
                "include_answer": True,
                "topic": normalized_topic,
            }
            if include_domains is not None:
                search_kwargs["include_domains"] = include_domains
            response: dict[str, Any] = await asyncio.to_thread(
                self.client.search,  # type: ignore[attr-defined]
                **search_kwargs,
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

    # to_dict inherited from SchemaToolMixin
