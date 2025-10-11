from .web_search_tools import SearchResult, WebSearchResponse

mock_responses = {
    "python programming": WebSearchResponse(
        results=[
            SearchResult(
                title="Python Programming Language - Official Website",
                snippet="Python is a high-level, interpreted programming language known for its "
                "simplicity and readability. Latest version is Python 3.13 with improved "
                "performance and new features.",
                url="https://python.org",
                relevance_score=0.95,
                source_type="official",
            ),
            SearchResult(
                title="Python Documentation",
                snippet="Complete documentation for Python standard library and language "
                "reference.",
                url="https://docs.python.org",
                relevance_score=0.88,
                source_type="documentation",
            ),
        ],
        total_results=2,
        search_query="python programming",
        source="mock_search",
    )
}
