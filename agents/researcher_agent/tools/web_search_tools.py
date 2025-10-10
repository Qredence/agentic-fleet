from typing import List

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Individual search result with metadata."""

    title: str = Field(..., description="Title of the search result")
    snippet: str = Field(..., description="Brief description or snippet")
    url: str = Field(..., description="Source URL")
    relevance_score: float = Field(..., description="Relevance score from 0.0 to 1.0")
    source_type: str = Field("web", description="Type of source")


class WebSearchResponse(BaseModel):
    """Structured response from web search."""

    results: List[SearchResult] = Field(..., description="List of search results")
    total_results: int = Field(..., description="Total number of results found")
    search_query: str = Field(..., description="Original search query")
    source: str = Field(..., description="Search source identifier")


def web_search_tool(query: str) -> WebSearchResponse:
    """
    Search the web for current information on a given query.

    Args:
        query: The search query to look up

    Returns:
        WebSearchResponse: Structured search results with relevance scores
    """
    # Mock implementation for Phase 1
    # In Phase 2, integrate with actual search APIs (Google, Bing, etc.)

    mock_responses = {
        "python programming": WebSearchResponse(
            results=[
                SearchResult(
                    title="Python Programming Language - Official Website",
                    snippet="Python is a high-level, interpreted programming language known for its simplicity and readability. Latest version is Python 3.13 with improved performance and new features.",
                    url="https://python.org",
                    relevance_score=0.95,
                    source_type="official",
                ),
                SearchResult(
                    title="Python Documentation",
                    snippet="Complete documentation for Python standard library and language reference.",
                    url="https://docs.python.org",
                    relevance_score=0.88,
                    source_type="documentation",
                ),
            ],
            total_results=2,
            search_query=query,
            source="mock_search",
        )
    }

    # Return mock response for known queries, generic for others
    if query.lower() in mock_responses:
        return mock_responses[query.lower()]
    else:
        return WebSearchResponse(
            results=[
                SearchResult(
                    title=f"Search Results for: {query}",
                    snippet="This would return real search results in production implementation. For Phase 1, this is a mock response demonstrating the structured data format.",
                    url="https://example.com/search",
                    relevance_score=0.7,
                    source_type="generic",
                )
            ],
            total_results=1,
            search_query=query,
            source="mock_search",
        )
