"""Tests for tool-aware DSPy supervisor functionality."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from agentic_fleet.dspy_modules.supervisor import DSPySupervisor
from agentic_fleet.utils.models import ExecutionMode, RoutingDecision
from agentic_fleet.utils.tool_registry import ToolRegistry


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str):
        self.name = name
        self.description = f"{name} description"
        self.additional_properties: dict[str, Any] | None = {}

    @property
    def schema(self):
        return {"type": "function", "function": {"name": self.name}}

    async def run(self, **_: Any) -> str:  # pragma: no cover - simple stub
        return f"{self.name} executed"

    def __str__(self) -> str:
        return self.name


@pytest.fixture
def tool_registry():
    """Create a tool registry with test tools."""
    registry = ToolRegistry()
    tool1 = MockTool("TavilySearchTool")
    tool2 = MockTool("HostedCodeInterpreterTool")
    registry.register_tool("TavilySearchTool", tool1, "Researcher")
    registry.register_tool("HostedCodeInterpreterTool", tool2, "Analyst")
    return registry


@pytest.fixture
def supervisor():
    """Create a DSPy supervisor instance."""
    return DSPySupervisor()


def test_set_tool_registry(supervisor, tool_registry):
    """Test setting tool registry on supervisor."""
    supervisor.set_tool_registry(tool_registry)
    assert supervisor.tool_registry is not None
    assert supervisor.tool_registry == tool_registry


def test_analyze_task_without_tools(supervisor):
    """Test task analysis without tool registry."""
    with patch("agentic_fleet.dspy_modules.supervisor.dspy"):
        mock_prediction = Mock()
        mock_prediction.complexity = "moderate"
        mock_prediction.required_capabilities = "research, analysis"
        mock_prediction.estimated_steps = "5"
        mock_prediction.tool_requirements = ""

        mock_chain = Mock()
        mock_chain.return_value = mock_prediction
        supervisor.task_analyzer = mock_chain

        result = supervisor.analyze_task("Test task", use_tools=False)

        assert result["complexity"] == "moderate"
        assert "capabilities" in result
        assert "tool_requirements" in result


def test_analyze_task_with_tools(supervisor, tool_registry):
    """Test task analysis with tool registry."""
    supervisor.set_tool_registry(tool_registry)

    with patch("agentic_fleet.dspy_modules.supervisor.dspy"):
        mock_prediction = Mock()
        mock_prediction.complexity = "moderate"
        mock_prediction.required_capabilities = "research"
        mock_prediction.estimated_steps = "3"
        mock_prediction.tool_requirements = "web_search"
        mock_prediction.needs_web_search = "no"
        mock_prediction.search_query = ""

        mock_chain = Mock()
        mock_chain.return_value = mock_prediction
        supervisor.tool_aware_analyzer = mock_chain

        result = supervisor.analyze_task("Test task", use_tools=True)

        assert result["complexity"] == "moderate"
        assert "tool_requirements" in result
        assert "search_context" in result


def test_route_task_with_tools(supervisor, tool_registry):
    """Test routing with tool awareness."""
    supervisor.set_tool_registry(tool_registry)

    with patch("agentic_fleet.dspy_modules.supervisor.dspy"):
        mock_prediction = Mock()
        mock_prediction.assigned_to = "Researcher"
        mock_prediction.execution_mode = "delegated"
        mock_prediction.subtasks = ""

        mock_chain = Mock()
        mock_chain.return_value = mock_prediction
        supervisor.task_router = mock_chain

        team = {"Researcher": "Web research specialist"}
        result = supervisor.route_task("Research task", team)

        assert list(result.assigned_to) == ["Researcher"]
        assert result.mode.value == "delegated"
        assert list(result.tool_requirements) == ["TavilySearchTool"]


def test_get_execution_summary_with_tools(supervisor, tool_registry):
    """Test execution summary includes tool usage stats."""
    supervisor.set_tool_registry(tool_registry)

    # Add some routing history
    supervisor.routing_history = [
        RoutingDecision(
            task="Test",
            assigned_to=("Researcher",),
            mode=ExecutionMode.DELEGATED,
            tool_requirements=("TavilySearchTool",),
        )
    ]

    summary = supervisor.get_execution_summary()

    assert "tool_usage_stats" in summary
    assert summary["tool_usage_stats"]["TavilySearchTool"] == 1


def test_parse_tool_requirements(supervisor):
    """Test parsing tool requirements from string."""
    result = supervisor._parse_tool_requirements("web_search, code_execution")
    assert result == ["web_search", "code_execution"]

    result = supervisor._parse_tool_requirements("web_search\ncode_execution")
    assert result == ["web_search", "code_execution"]

    result = supervisor._parse_tool_requirements("")
    assert result == []
