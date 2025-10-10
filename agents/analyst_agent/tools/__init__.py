"""
Analyst Agent Tools Package
===========================

This package contains tools for data analysis and visualization.

Tools:
    - data_analysis_tool: Analyzes data and provides structured insights
    - visualization_suggestion_tool: Suggests appropriate visualizations

Usage:
    from agents.analyst_agent.tools.data_analysis_tools import (
        data_analysis_tool,
        visualization_suggestion_tool
    )

    # Analyze data
    analysis = data_analysis_tool(data="Sales data: Q1=$100k, Q2=$150k...")
    for insight in analysis.insights:
        print(f"{insight.category}: {insight.description}")

    # Get visualization suggestions
    viz = visualization_suggestion_tool(data_type="time_series")
    print(f"Recommended: {viz.chart_type}")
"""

from agents.analyst_agent.tools.data_analysis_tools import (
    data_analysis_tool,
    visualization_suggestion_tool,
)

__all__ = ["data_analysis_tool", "visualization_suggestion_tool"]
