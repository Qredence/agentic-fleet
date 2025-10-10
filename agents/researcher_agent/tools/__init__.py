"""
Researcher Agent Tools Package
==============================

This package contains tools for web research and information gathering.

Tools:
    - web_search_tool: Performs web searches and returns structured results

Usage:
    from agents.researcher_agent.tools.web_search_tools import web_search_tool

    response = web_search_tool("Python machine learning libraries")
    for result in response.results:
        print(f"{result.title}: {result.url}")
"""

from agents.researcher_agent.tools.web_search_tools import web_search_tool

__all__ = ["web_search_tool"]
