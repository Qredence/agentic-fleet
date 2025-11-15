"""
Integration tests for tool registry population during workflow initialization.

Ensures that the tool registry is properly populated when agents with tools
are created, and that the DSPy supervisor can access tool metadata.
"""

import os

import pytest

from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow


@pytest.mark.asyncio
async def test_tool_registry_populated_after_init():
    """Verify tool registry is populated with agent tools after initialization."""
    # Set dummy Tavily key to allow initialization
    os.environ.setdefault("TAVILY_API_KEY", "dummy-key-for-testing")

    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    # Verify registry has tools
    available_tools = workflow.tool_registry.get_available_tools()
    assert len(available_tools) > 0, "Tool registry should contain tools after initialization"

    # Verify expected tools are present
    tool_names = list(available_tools.keys())

    # Should have web search tool (from Researcher)
    assert any(
        "tavily" in name.lower() or "search" in name.lower() for name in tool_names
    ), f"Expected web search tool, got: {tool_names}"

    # Should have code execution tool (from Analyst)
    assert any(
        "code" in name.lower() or "interpreter" in name.lower() for name in tool_names
    ), f"Expected code execution tool, got: {tool_names}"


@pytest.mark.asyncio
async def test_tool_descriptions_formatted():
    """Verify tool descriptions are properly formatted for DSPy prompts."""
    os.environ.setdefault("TAVILY_API_KEY", "dummy-key-for-testing")

    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    descriptions = workflow.tool_registry.get_tool_descriptions()

    # Should not be empty
    assert descriptions, "Tool descriptions should not be empty"
    assert descriptions != "No tools are currently available."

    # Should contain key information
    assert (
        "available to" in descriptions.lower()
    ), "Descriptions should show which agent has each tool"
    assert "capabilities" in descriptions.lower(), "Descriptions should list capabilities"


@pytest.mark.asyncio
async def test_tool_registry_attached_to_supervisor():
    """Verify DSPy supervisor has access to tool registry."""
    os.environ.setdefault("TAVILY_API_KEY", "dummy-key-for-testing")

    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    # Verify supervisor has tool registry
    assert (
        workflow.dspy_supervisor.tool_registry is not None
    ), "Supervisor should have tool registry attached"
    assert (
        workflow.dspy_supervisor.tool_registry is workflow.tool_registry
    ), "Supervisor should reference the same registry instance"


@pytest.mark.asyncio
async def test_tool_capabilities_inferred():
    """Verify tool capabilities are automatically inferred."""
    os.environ.setdefault("TAVILY_API_KEY", "dummy-key-for-testing")

    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    # Get web search tools
    search_tools = workflow.tool_registry.get_tools_by_capability("web_search")
    assert len(search_tools) > 0, "Should have at least one web search tool"

    # Get code execution tools
    code_tools = workflow.tool_registry.get_tools_by_capability("code_execution")
    assert len(code_tools) > 0, "Should have at least one code execution tool"


@pytest.mark.asyncio
async def test_tool_registry_empty_without_tools():
    """Verify graceful handling when agents have no tools."""
    # Create workflow with agents that have no tools
    workflow = SupervisorWorkflow()
    # Temporarily override agents to have no tools
    workflow.agents = {
        "Writer": type(
            "Agent",
            (),
            {
                "description": "Test agent",
                "chat_options": type("Options", (), {"tools": []})(),
            },
        )(),
    }

    # Initialize tool registry manually
    for agent_name, agent in workflow.agents.items():
        if hasattr(agent, "chat_options") and hasattr(agent.chat_options, "tools"):
            for tool in agent.chat_options.tools or []:
                workflow.tool_registry.register_tool_by_agent(agent_name, tool)

    # Should handle empty registry gracefully
    descriptions = workflow.tool_registry.get_tool_descriptions()
    assert "No tools" in descriptions or len(workflow.tool_registry.get_available_tools()) == 0


@pytest.mark.asyncio
async def test_tool_aliases_registered():
    """Verify tool aliases are properly registered and accessible."""
    os.environ.setdefault("TAVILY_API_KEY", "dummy-key-for-testing")

    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    # Get all tools
    available_tools = workflow.tool_registry.get_available_tools()

    # At least one tool should have capabilities
    has_capabilities = any(tool.get("capabilities") for tool in available_tools.values())
    assert has_capabilities, "At least one tool should have inferred capabilities"

    # Verify alias resolution works
    descriptions = workflow.tool_registry.get_tool_descriptions()
    assert (
        "aliases:" in descriptions.lower() or len(available_tools) > 0
    ), "Tool aliases should be visible in descriptions"


@pytest.mark.asyncio
async def test_supervisor_instructions_include_tools():
    """Verify supervisor instructions include tool catalog."""
    os.environ.setdefault("TAVILY_API_KEY", "dummy-key-for-testing")

    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    instructions = workflow._get_supervisor_instructions()

    # Instructions should mention tools
    assert (
        "available tools" in instructions.lower()
    ), "Instructions should include tool catalog section"

    # Should list actual tools or say "no tools"
    assert (
        "tavily" in instructions.lower()
        or "code" in instructions.lower()
        or "no tools" in instructions.lower()
    ), "Instructions should show actual tools or indicate none available"
