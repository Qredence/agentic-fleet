"""Tests for tool registry functionality."""

from typing import Any

from agentic_fleet.utils.tool_registry import ToolRegistry


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.additional_properties: dict[str, Any] | None = {}

    @property
    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
            },
        }

    def __str__(self) -> str:
        return self.name

    async def run(self, query: str) -> str:
        return f"Result for {query}"


def test_tool_registry_initialization():
    """Test that tool registry initializes correctly."""
    registry = ToolRegistry()
    assert len(registry.get_available_tools()) == 0
    assert registry.get_tool_descriptions() == "No tools are currently available."


def test_register_tool():
    """Test registering a tool."""
    registry = ToolRegistry()
    tool = MockTool("test_tool", "A test tool")

    registry.register_tool("test_tool", tool, "TestAgent")

    assert len(registry.get_available_tools()) == 1
    assert "test_tool" in registry.get_available_tools()
    tool_meta = registry.get_tool("test_tool")
    assert tool_meta is not None
    assert tool_meta.agent == "TestAgent"


def test_get_agent_tools():
    """Test getting tools for a specific agent."""
    registry = ToolRegistry()
    tool1 = MockTool("tool1", "First tool")
    tool2 = MockTool("tool2", "Second tool")

    registry.register_tool("tool1", tool1, "Agent1")
    registry.register_tool("tool2", tool2, "Agent2")

    agent1_tools = registry.get_agent_tools("Agent1")
    assert len(agent1_tools) == 1
    assert agent1_tools[0].name == "tool1"

    agent2_tools = registry.get_agent_tools("Agent2")
    assert len(agent2_tools) == 1
    assert agent2_tools[0].name == "tool2"


def test_get_tool_descriptions():
    """Test getting formatted tool descriptions."""
    registry = ToolRegistry()
    tool = MockTool("search_tool", "Web search tool")

    registry.register_tool("search_tool", tool, "Researcher")

    descriptions = registry.get_tool_descriptions()
    assert "search_tool" in descriptions
    assert "Researcher" in descriptions
    assert "Web search tool" in descriptions


def test_get_tools_by_capability():
    """Test getting tools by capability."""
    registry = ToolRegistry()
    tool = MockTool("tavily_search", "Tavily web search")

    registry.register_tool("tavily_search", tool, "Researcher")

    search_tools = registry.get_tools_by_capability("web_search")
    assert len(search_tools) == 1
    assert search_tools[0].name == "tavily_search"


def test_can_execute_tool():
    """Test checking if a tool can be executed."""
    registry = ToolRegistry()
    tool = MockTool("test_tool", "Test tool")

    registry.register_tool("test_tool", tool, "TestAgent")

    assert registry.can_execute_tool("test_tool") is True
    assert registry.can_execute_tool("nonexistent") is False


def test_register_tool_by_agent():
    """Test registering tool via agent method."""
    registry = ToolRegistry()
    tool = MockTool("agent_tool", "Agent tool")

    registry.register_tool_by_agent("TestAgent", tool)

    assert len(registry.get_available_tools()) == 1
    agent_tools = registry.get_agent_tools("TestAgent")
    assert len(agent_tools) == 1
    assert agent_tools[0].name == "agent_tool"


def test_clear_registry():
    """Test clearing the registry."""
    registry = ToolRegistry()
    tool = MockTool("test_tool", "Test tool")

    registry.register_tool("test_tool", tool, "TestAgent")
    assert len(registry.get_available_tools()) == 1

    registry.clear()
    assert len(registry.get_available_tools()) == 0
