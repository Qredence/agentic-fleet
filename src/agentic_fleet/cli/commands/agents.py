"""Agents command for listing available agents."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ...utils.env import env_config

console = Console()


def list_agents() -> None:
    """List all available agents and their capabilities."""
    # Check tool availability
    tavily_available = bool(env_config.tavily_api_key)

    agents_info = [
        {
            "name": "Researcher",
            "description": "Information gathering and web research specialist",
            "tools": [
                f"TavilySearchTool {'(enabled)' if tavily_available else '(missing TAVILY_API_KEY)'}"
            ],
            "best_for": "Finding information, fact-checking, research",
        },
        {
            "name": "Analyst",
            "description": "Data analysis and computation specialist",
            "tools": ["HostedCodeInterpreterTool"],
            "best_for": "Data analysis, calculations, visualizations",
        },
        {
            "name": "Writer",
            "description": "Content creation and report writing specialist",
            "tools": ["None"],
            "best_for": "Writing, documentation, content creation",
        },
        {
            "name": "Reviewer",
            "description": "Quality assurance and validation specialist",
            "tools": ["None"],
            "best_for": "Review, validation, quality checks",
        },
    ]

    table = Table(title="Available Agents", show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan", width=12)
    table.add_column("Description", style="yellow", width=40)
    table.add_column("Tools", style="green", width=30)
    table.add_column("Best For", style="blue", width=30)

    for agent in agents_info:
        tools_str = ", ".join(agent["tools"])
        table.add_row(
            str(agent["name"]),
            str(agent["description"]),
            str(tools_str),
            str(agent["best_for"]),
        )

    console.print(table)
