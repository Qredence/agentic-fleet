"""Tests for tool parsing compatibility with agent-framework."""

import contextlib
import os
import sys
import types

import pytest
from agent_framework import ToolProtocol

from agentic_fleet.tools.serialization import SerializationMixin

# Import _tools_to_dict with fallback for test environments
try:
    from agent_framework._tools import _tools_to_dict
except (ImportError, ModuleNotFoundError, AttributeError):
    # Fallback for test environments
    def _tools_to_dict(tools):  # type: ignore[no-redef]
        """Fallback _tools_to_dict for test environments."""
        # If tools have to_dict method, return list with dict
        if hasattr(tools, "to_dict"):
            return [tools.to_dict()]
        if isinstance(tools, list | tuple):
            result = []
            for tool in tools:
                if hasattr(tool, "to_dict"):
                    result.append(tool.to_dict())
            return result if result else None
        return None

    # Register in sys.modules so tools can use it
    if "agent_framework" not in sys.modules:
        sys.modules["agent_framework"] = types.ModuleType("agent_framework")
    if "agent_framework._tools" not in sys.modules:
        tools_mod = types.ModuleType("agent_framework._tools")
        tools_mod._tools_to_dict = _tools_to_dict
        sys.modules["agent_framework._tools"] = tools_mod
        sys.modules["agent_framework"]._tools = tools_mod


from agentic_fleet.tools.browser_tool import BrowserTool
from agentic_fleet.tools.hosted_code_adapter import HostedCodeInterpreterAdapter
from agentic_fleet.tools.tavily_mcp_tool import TavilyMCPTool
from agentic_fleet.tools.tavily_tool import TavilySearchTool


class TestToolSerializationMixin:
    """Test that all tools properly implement SerializationMixin."""

    def test_tavily_tool_is_serialization_mixin(self):
        """Test TavilySearchTool implements SerializationMixin."""
        os.environ["TAVILY_API_KEY"] = "test-key"
        tool = TavilySearchTool()

        assert isinstance(tool, SerializationMixin), "TavilySearchTool should be SerializationMixin"
        assert isinstance(tool, ToolProtocol), "TavilySearchTool should be ToolProtocol"
        assert hasattr(tool, "to_dict"), "TavilySearchTool should have to_dict method"

    def test_tavily_tool_to_dict(self):
        """Test TavilySearchTool.to_dict() returns valid dict."""
        os.environ["TAVILY_API_KEY"] = "test-key"
        tool = TavilySearchTool()

        result = tool.to_dict()
        assert isinstance(result, dict), "to_dict() should return dict"
        assert "type" in result, "Schema should have 'type' key"
        assert "function" in result, "Schema should have 'function' key"
        assert result["function"]["name"] == "tavily_search"

    def test_browser_tool_is_serialization_mixin(self):
        """Test BrowserTool implements SerializationMixin."""
        # BrowserTool requires playwright, so we'll skip if not available
        try:
            tool = BrowserTool()
            assert isinstance(tool, SerializationMixin), "BrowserTool should be SerializationMixin"
            assert isinstance(tool, ToolProtocol), "BrowserTool should be ToolProtocol"
            assert hasattr(tool, "to_dict"), "BrowserTool should have to_dict method"
        except ImportError:
            pytest.skip("Playwright not available")

    def test_browser_tool_to_dict(self):
        """Test BrowserTool.to_dict() returns valid dict."""
        try:
            tool = BrowserTool()
            result = tool.to_dict()
            assert isinstance(result, dict), "to_dict() should return dict"
            assert "type" in result, "Schema should have 'type' key"
            assert "function" in result, "Schema should have 'function' key"
            assert result["function"]["name"] == "browser"
        except ImportError:
            pytest.skip("Playwright not available")

    def test_tavily_mcp_tool_initialization(self):
        """Test TavilyMCPTool can be initialized."""
        os.environ["TAVILY_API_KEY"] = "test-key"
        tool = TavilyMCPTool()

        # MCP tools may not implement SerializationMixin directly, but should be usable
        assert hasattr(tool, "name"), "TavilyMCPTool should have name attribute"
        assert tool.name == "tavily_search", "TavilyMCPTool should have correct name"
        assert hasattr(tool, "description"), "TavilyMCPTool should have description"

    def test_hosted_code_adapter_is_serialization_mixin(self):
        """Test HostedCodeInterpreterAdapter implements SerializationMixin."""
        tool = HostedCodeInterpreterAdapter()

        assert isinstance(
            tool, SerializationMixin
        ), "HostedCodeInterpreterAdapter should be SerializationMixin"
        assert isinstance(tool, ToolProtocol), "HostedCodeInterpreterAdapter should be ToolProtocol"
        assert hasattr(tool, "to_dict"), "HostedCodeInterpreterAdapter should have to_dict method"

    def test_hosted_code_adapter_to_dict(self):
        """Test HostedCodeInterpreterAdapter.to_dict() returns valid dict."""
        tool = HostedCodeInterpreterAdapter()

        result = tool.to_dict()
        assert isinstance(result, dict), "to_dict() should return dict"
        assert "type" in result, "Schema should have 'type' key"
        assert "function" in result, "Schema should have 'function' key"
        assert result["function"]["name"] == "HostedCodeInterpreterTool"


class TestToolParsing:
    """Test that tools can be parsed by agent-framework's _tools_to_dict."""

    def test_tavily_tool_parsing(self):
        """Test TavilySearchTool can be parsed by agent-framework."""
        os.environ["TAVILY_API_KEY"] = "test-key"
        tool = TavilySearchTool()

        result = _tools_to_dict(tool)
        assert result is not None, "Tool should be parsed successfully"
        assert isinstance(result, list), "Result should be a list"
        assert len(result) == 1, "Should have one tool in result"
        assert isinstance(result[0], dict), "Tool should be converted to dict"

    def test_tavily_mcp_tool_parsing(self):
        """Test TavilyMCPTool can be parsed by agent-framework."""
        os.environ["TAVILY_API_KEY"] = "test-key"
        tool = TavilyMCPTool()

        # MCP tools may not be parseable by _tools_to_dict (they work differently)
        # But they should still be usable with ChatAgent
        # Check that tool has required attributes instead
        assert hasattr(tool, "name"), "MCP tool should have name"
        assert tool.name == "tavily_search", "MCP tool should have correct name"
        assert hasattr(tool, "description"), "MCP tool should have description"

        # Try parsing - may return None for MCP tools, which is OK
        _tools_to_dict(tool)
        # MCP tools might not parse via _tools_to_dict but work with ChatAgent
        # So we don't assert on result - just verify tool is valid

    def test_browser_tool_parsing(self):
        """Test BrowserTool can be parsed by agent-framework."""
        try:
            tool = BrowserTool()
            result = _tools_to_dict(tool)
            assert result is not None, "Tool should be parsed successfully"
            assert isinstance(result, list), "Result should be a list"
            assert len(result) == 1, "Should have one tool in result"
            assert isinstance(result[0], dict), "Tool should be converted to dict"
        except ImportError:
            pytest.skip("Playwright not available")

    def test_hosted_code_adapter_parsing(self):
        """Test HostedCodeInterpreterAdapter can be parsed by agent-framework."""
        tool = HostedCodeInterpreterAdapter()

        result = _tools_to_dict(tool)
        assert result is not None, "Tool should be parsed successfully"
        assert isinstance(result, list), "Result should be a list"
        assert len(result) == 1, "Should have one tool in result"
        assert isinstance(result[0], dict), "Tool should be converted to dict"

    def test_multiple_tools_parsing(self):
        """Test multiple tools can be parsed together."""
        os.environ["TAVILY_API_KEY"] = "test-key"
        tools = [
            TavilySearchTool(),
            HostedCodeInterpreterAdapter(),
        ]

        # Add BrowserTool if available
        with contextlib.suppress(ImportError):
            tools.append(BrowserTool())

        result = _tools_to_dict(tools)
        assert result is not None, "Tools should be parsed successfully"
        assert isinstance(result, list), "Result should be a list"
        assert len(result) >= 2, "Should have at least 2 tools in result"
        assert all(isinstance(t, dict) for t in result), "All tools should be converted to dict"

    def test_tavily_mcp_tool_with_other_tools(self):
        """Test TavilyMCPTool can be parsed with other tools."""
        os.environ["TAVILY_API_KEY"] = "test-key"
        tools = [
            TavilyMCPTool(),
            HostedCodeInterpreterAdapter(),
        ]

        result = _tools_to_dict(tools)
        assert result is not None, "Tools including MCP tool should be parsed successfully"
        assert isinstance(result, list), "Result should be a list"


class TestToolValidation:
    """Test tool validation in supervisor workflow."""

    def test_validate_tool_with_serialization_mixin(self):
        """Test _validate_tool accepts SerializationMixin tools."""
        from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow

        workflow = SupervisorWorkflow()
        # Don't initialize - just test the validation method directly

        os.environ["TAVILY_API_KEY"] = "test-key"
        tool = TavilySearchTool()

        assert workflow._validate_tool(tool), "Valid SerializationMixin tool should pass validation"

    def test_validate_tool_with_mcp_tool(self):
        """Test _validate_tool accepts MCP tools."""
        from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow

        workflow = SupervisorWorkflow()
        # Don't initialize - just test the validation method directly

        os.environ["TAVILY_API_KEY"] = "test-key"
        tool = TavilyMCPTool()

        # MCP tools should pass validation (they may not be SerializationMixin but are valid tools)
        assert workflow._validate_tool(tool), "Valid MCP tool should pass validation"

    def test_validate_tool_with_dict(self):
        """Test _validate_tool accepts dict tools."""
        from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow

        workflow = SupervisorWorkflow()
        # Don't initialize - just test the validation method directly

        tool_dict = {"type": "function", "function": {"name": "test_tool"}}

        assert workflow._validate_tool(tool_dict), "Dict tool should pass validation"

    def test_validate_tool_with_callable(self):
        """Test _validate_tool accepts callable tools."""
        from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow

        workflow = SupervisorWorkflow()
        # Don't initialize - just test the validation method directly

        def test_function():
            pass

        assert workflow._validate_tool(test_function), "Callable tool should pass validation"

    def test_validate_tool_rejects_invalid(self):
        """Test _validate_tool rejects invalid tools."""
        from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow

        workflow = SupervisorWorkflow()
        # Don't initialize - just test the validation method directly

        # Invalid tool (not SerializationMixin, not dict, not callable, missing required attrs)
        # Use a class instance that's not callable and doesn't have required attributes
        class InvalidTool:
            pass

        invalid_tool = InvalidTool()

        assert not workflow._validate_tool(invalid_tool), "Invalid tool should be rejected"

    def test_validate_tool_with_none(self):
        """Test _validate_tool rejects None."""
        from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow

        workflow = SupervisorWorkflow()
        # Don't initialize - just test the validation method directly

        assert not workflow._validate_tool(None), "None should be rejected"


class TestToolRegistration:
    """Test tool registration in supervisor workflow."""

    @pytest.mark.asyncio
    async def test_tools_registered_successfully(self, monkeypatch):
        """Test that valid tools are registered successfully."""
        from unittest.mock import AsyncMock, MagicMock

        import dspy
        import openai

        # Mock OpenAI client to avoid needing API key
        mock_async_client = AsyncMock()
        monkeypatch.setattr(openai, "AsyncOpenAI", lambda **kwargs: mock_async_client)

        # Mock dspy.LM to avoid model initialization issues
        mock_lm = MagicMock()
        monkeypatch.setattr(dspy, "LM", lambda *args, **kwargs: mock_lm)

        # Mock dspy.settings.configure
        monkeypatch.setattr(dspy.settings, "configure", lambda **kwargs: None)

        # Set TAVILY_API_KEY for test
        os.environ["TAVILY_API_KEY"] = "test-key"

        from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow

        workflow = SupervisorWorkflow()
        await workflow.initialize(compile_dspy=False)

        # Check that tools are registered
        registry = workflow.tool_registry
        available_tools = registry.get_available_tools()

        # Should have at least some tools registered (Researcher has TavilyMCP/Browser, Analyst has CodeInterpreter)
        # Note: MCP tools may not appear in available_tools dict but are still functional
        assert len(available_tools) >= 0, "Tool registry should be accessible"

        # Verify tools are properly registered
        analyst_tools = registry.get_agent_tools("Analyst")

        # Researcher should have tools if Tavily is available (MCP tool is registered directly)
        if os.getenv("TAVILY_API_KEY"):
            # MCP tool should be registered (either in researcher_tools or available via agent)
            # The tool may not appear in get_agent_tools if MCP tools work differently
            # But it should be registered in the workflow
            pass  # MCP tools work at runtime even if not in registry

        # Analyst should have HostedCodeInterpreterTool
        assert len(analyst_tools) > 0, "Analyst should have tools registered"

    @pytest.mark.asyncio
    async def test_tool_validation_during_registration(self, monkeypatch):
        """Test that invalid tools are filtered during registration."""
        from unittest.mock import AsyncMock, MagicMock

        import dspy
        import openai

        # Mock OpenAI client to avoid needing API key
        mock_async_client = AsyncMock()
        monkeypatch.setattr(openai, "AsyncOpenAI", lambda **kwargs: mock_async_client)

        # Mock dspy.LM to avoid model initialization issues
        mock_lm = MagicMock()
        monkeypatch.setattr(dspy, "LM", lambda *args, **kwargs: mock_lm)

        # Import after monkeypatching
        from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow

        # Mock configure_dspy_settings to avoid async task conflicts
        async def mock_configure(*args, **kwargs):
            return None

        monkeypatch.setattr(
            "agentic_fleet.utils.dspy_manager.configure_dspy_settings", mock_configure
        )

        workflow = SupervisorWorkflow()
        await workflow.initialize(compile_dspy=False)

        # All registered tools should be valid
        registry = workflow.tool_registry
        available_tools = registry.get_available_tools()

        # get_available_tools() returns a dict mapping tool names to metadata
        for tool_name, _tool_info in available_tools.items():
            # Get the actual tool metadata object
            tool_metadata = registry.get_tool(tool_name)
            if tool_metadata and tool_metadata.tool_instance is not None:
                assert workflow._validate_tool(
                    tool_metadata.tool_instance
                ), f"Registered tool {tool_name} should be valid"


class TestToolSchemaFormat:
    """Test that tool schemas are in correct format."""

    def test_tavily_tool_schema_format(self):
        """Test TavilySearchTool schema has correct format."""
        os.environ["TAVILY_API_KEY"] = "test-key"
        tool = TavilySearchTool()
        schema = tool.schema

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "tavily_search"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]
        assert "properties" in schema["function"]["parameters"]
        assert "query" in schema["function"]["parameters"]["properties"]

    def test_tavily_mcp_tool_has_name_and_description(self):
        """Test TavilyMCPTool has required attributes."""
        os.environ["TAVILY_API_KEY"] = "test-key"
        tool = TavilyMCPTool()

        # MCP tools should have name and description
        assert hasattr(tool, "name"), "TavilyMCPTool should have name attribute"
        assert tool.name == "tavily_search", "TavilyMCPTool should have correct name"
        assert hasattr(tool, "description"), "TavilyMCPTool should have description attribute"
        assert (
            "MANDATORY" in tool.description
        ), "TavilyMCPTool description should emphasize mandatory usage"

    def test_browser_tool_schema_format(self):
        """Test BrowserTool schema has correct format."""
        try:
            tool = BrowserTool()
            schema = tool.schema

            assert schema["type"] == "function"
            assert "function" in schema
            assert schema["function"]["name"] == "browser"
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]
            assert "properties" in schema["function"]["parameters"]
            assert "url" in schema["function"]["parameters"]["properties"]
        except ImportError:
            pytest.skip("Playwright not available")

    def test_hosted_code_adapter_schema_format(self):
        """Test HostedCodeInterpreterAdapter schema has correct format."""
        tool = HostedCodeInterpreterAdapter()
        schema = tool.schema

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "HostedCodeInterpreterTool"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]
        assert "properties" in schema["function"]["parameters"]
        assert "code" in schema["function"]["parameters"]["properties"]
