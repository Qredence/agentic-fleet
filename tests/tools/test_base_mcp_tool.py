"""Tests for BaseMCPTool base class.

These tests verify the shared functionality provided by BaseMCPTool including
connection management, tool name resolution, safe disconnection, and content formatting.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest


# We need to import BaseMCPTool without triggering the tools __init__.py
# which has import issues with agent_framework
def _import_base_mcp_tool():
    """
    Load and return the BaseMCPTool class by importing its module directly from the source file.

    This helper ensures a minimal mock of agent_framework._mcp is available in sys.modules (so imports that expect MCPStreamableHTTPTool succeed), then loads the base_mcp_tool module from its file path and returns its BaseMCPTool class. The function may add a mock module to sys.modules as a side effect and will raise an AssertionError if the module spec or loader cannot be created.

    Returns:
        type: The BaseMCPTool class object from the loaded module.
    """
    # First, ensure we have a fallback MCPStreamableHTTPTool
    if "agent_framework._mcp" not in sys.modules:
        mock_mcp = MagicMock()

        class MockMCPStreamableHTTPTool:
            """Mock MCP tool for testing."""

            def __init__(self, *args: Any, **kwargs: Any):
                self.name = kwargs.get("name", "mcp_tool")
                self.description = kwargs.get("description", "")
                self.session = None
                self.is_connected = False
                self.functions: list[Any] = []

            async def connect(self) -> None:
                """Mock connect method."""
                self.session = MagicMock()
                self.is_connected = True

            async def call_tool(self, tool_name: str, **kwargs: Any) -> list[Any]:
                """Mock call_tool method."""
                return []

            async def disconnect(self) -> None:
                """Mock disconnect method."""
                self.session = None
                self.is_connected = False

        mock_mcp.MCPStreamableHTTPTool = MockMCPStreamableHTTPTool
        sys.modules["agent_framework._mcp"] = mock_mcp

    # Import the module directly from file path
    module_path = (
        Path(__file__).parent.parent.parent / "src" / "agentic_fleet" / "tools" / "base_mcp_tool.py"
    )
    spec = importlib.util.spec_from_file_location("base_mcp_tool", module_path)
    assert spec is not None, "Failed to load module spec"
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None, "Spec has no loader"
    spec.loader.exec_module(module)
    return module.BaseMCPTool


BaseMCPTool = _import_base_mcp_tool()


class ConcreteMCPTool(BaseMCPTool):
    """Concrete implementation of BaseMCPTool for testing."""

    async def run(self, query: str, **kwargs: Any) -> str:
        """Execute the tool with the given query."""
        await self._ensure_connection()
        tool_name = self._resolve_remote_tool_name()
        contents = await self.call_tool(tool_name, query=query)
        result = self._format_contents(contents)
        await self._safe_disconnect()
        return result or "Empty response"


class TestBaseMCPToolInitialization:
    """Test BaseMCPTool initialization."""

    def test_init_sets_name_and_description(self):
        """Test that initialization sets name and description correctly."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        assert tool.name == "test_tool"
        assert tool.description == "Test description"

    def test_init_creates_connect_lock(self):
        """Test that initialization creates an asyncio Lock."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        assert isinstance(tool._connect_lock, asyncio.Lock)

    def test_init_resolved_tool_name_is_none(self):
        """Test that resolved tool name starts as None."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        assert tool._resolved_tool_name is None


class TestEnsureConnection:
    """Test _ensure_connection method."""

    @pytest.mark.asyncio
    async def test_connects_when_not_connected(self):
        """Test that _ensure_connection connects when session is not connected."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        tool.connect = AsyncMock()
        await tool._ensure_connection()

        tool.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_reconnect_when_already_connected(self):
        """Test that _ensure_connection doesn't reconnect when already connected."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        # Simulate already connected state
        tool.session = MagicMock()
        tool.is_connected = True
        tool.connect = AsyncMock()

        await tool._ensure_connection()

        tool.connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_double_checked_locking_prevents_concurrent_connections(self):
        """Test that double-checked locking prevents race conditions."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        call_count = 0

        async def slow_connect():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            tool.session = MagicMock()
            tool.is_connected = True

        tool.connect = slow_connect

        # Start multiple concurrent connection attempts
        await asyncio.gather(
            tool._ensure_connection(),
            tool._ensure_connection(),
            tool._ensure_connection(),
        )

        # Should only connect once despite multiple concurrent calls
        assert call_count == 1


class TestResolveRemoteToolName:
    """Test _resolve_remote_tool_name method."""

    def test_returns_cached_name_if_available(self):
        """Test that cached tool name is returned if available."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        tool._resolved_tool_name = "cached_tool"

        result = tool._resolve_remote_tool_name()

        assert result == "cached_tool"

    def test_matches_keyword_in_function_name(self):
        """Test that function names matching keywords are preferred."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        # Create mock functions
        func1 = MagicMock()
        func1.name = "other_function"
        func2 = MagicMock()
        func2.name = "search_documents"

        # Use PropertyMock to mock the read-only functions property
        with patch.object(type(tool), "functions", new_callable=PropertyMock) as mock_funcs:
            mock_funcs.return_value = [func1, func2]

            result = tool._resolve_remote_tool_name()

            assert result == "search_documents"
            assert tool._resolved_tool_name == "search_documents"

    def test_uses_first_function_when_no_keyword_match(self):
        """Test that first function is used when no keyword matches."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        # Create mock functions with no matching keywords
        func1 = MagicMock()
        func1.name = "first_function"
        func2 = MagicMock()
        func2.name = "second_function"

        # Use PropertyMock to mock the read-only functions property
        with patch.object(type(tool), "functions", new_callable=PropertyMock) as mock_funcs:
            mock_funcs.return_value = [func1, func2]

            result = tool._resolve_remote_tool_name()

            assert result == "first_function"

    def test_falls_back_to_local_name_when_no_functions(self):
        """Test fallback to local name when no functions available."""
        tool = ConcreteMCPTool(
            name="fallback_name",
            url="https://example.com",
            description="Test description",
        )

        # Use PropertyMock to mock the read-only functions property
        with patch.object(type(tool), "functions", new_callable=PropertyMock) as mock_funcs:
            mock_funcs.return_value = []

            result = tool._resolve_remote_tool_name()

            assert result == "fallback_name"

    def test_custom_preferred_keywords(self):
        """Test that custom preferred keywords are used."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        func1 = MagicMock()
        func1.name = "search_function"
        func2 = MagicMock()
        func2.name = "custom_function"

        # Use PropertyMock to mock the read-only functions property
        with patch.object(type(tool), "functions", new_callable=PropertyMock) as mock_funcs:
            mock_funcs.return_value = [func1, func2]

            # Use custom keywords that match func2 instead of default
            result = tool._resolve_remote_tool_name(preferred_keywords=["custom"])

            assert result == "custom_function"


class TestSafeDisconnect:
    """Test _safe_disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnects_when_connected(self):
        """Test that _safe_disconnect calls disconnect when connected."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        tool.session = MagicMock()
        tool.is_connected = True
        tool.disconnect = AsyncMock()

        await tool._safe_disconnect()

        tool.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_disconnect_when_not_connected(self):
        """Test that _safe_disconnect is a no-op when not connected."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        tool.is_connected = False
        tool.disconnect = AsyncMock()

        await tool._safe_disconnect()

        tool.disconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_disconnect_exception_gracefully(self):
        """Test that _safe_disconnect handles exceptions without raising."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        tool.session = MagicMock()
        tool.is_connected = True
        tool.disconnect = AsyncMock(side_effect=Exception("Connection already closed"))

        # Should not raise
        await tool._safe_disconnect()


class TestFormatContents:
    """Test _format_contents static method."""

    def test_returns_empty_string_for_empty_contents(self):
        """Test that empty contents returns empty string."""
        result = BaseMCPTool._format_contents([])

        assert result == ""

    def test_formats_text_attribute(self):
        """Test formatting objects with text attribute."""
        item = MagicMock()
        item.text = "Hello, world!"
        del item.content  # Ensure content attribute doesn't exist

        result = BaseMCPTool._format_contents([item])

        assert result == "Hello, world!"

    def test_formats_content_attribute(self):
        """Test formatting objects with content attribute."""
        item = MagicMock(spec=["content"])
        item.content = "Content value"

        result = BaseMCPTool._format_contents([item])

        assert result == "Content value"

    def test_formats_dict_with_text_key(self):
        """Test formatting dict representation with text key."""
        item = MagicMock(spec=["to_dict"])
        item.to_dict.return_value = {"text": "Dict text value"}

        result = BaseMCPTool._format_contents([item])

        assert result == "Dict text value"

    def test_formats_dict_with_content_key(self):
        """Test formatting dict representation with content key."""
        item = MagicMock(spec=["to_dict"])
        item.to_dict.return_value = {"content": "Dict content value"}

        result = BaseMCPTool._format_contents([item])

        assert result == "Dict content value"

    def test_formats_dict_with_error_key(self):
        """Test formatting dict representation with error key."""
        item = MagicMock(spec=["to_dict"])
        item.to_dict.return_value = {"error": "Something went wrong"}

        result = BaseMCPTool._format_contents([item])

        assert result == "Error: Something went wrong"

    def test_formats_dict_with_data_key(self):
        """Test formatting dict representation with data key."""
        item = MagicMock(spec=["to_dict"])
        item.to_dict.return_value = {"data": {"key": "value"}}

        result = BaseMCPTool._format_contents([item])

        assert '"key": "value"' in result

    def test_joins_multiple_items_with_double_newlines(self):
        """Test that multiple items are joined with double newlines."""
        item1 = MagicMock()
        item1.text = "First item"
        del item1.content

        item2 = MagicMock()
        item2.text = "Second item"
        del item2.content

        result = BaseMCPTool._format_contents([item1, item2])

        assert result == "First item\n\nSecond item"

    def test_skips_empty_values(self):
        """Test that empty text values are skipped."""
        item1 = MagicMock()
        item1.text = "Valid text"
        del item1.content

        item2 = MagicMock()
        item2.text = ""  # Empty text
        del item2.content

        item3 = MagicMock()
        item3.text = "Another valid text"
        del item3.content

        result = BaseMCPTool._format_contents([item1, item2, item3])

        assert result == "Valid text\n\nAnother valid text"

    def test_falls_back_to_string_conversion(self):
        """Test fallback to string conversion for unknown types."""

        # Create a simple class without text/content/to_dict
        class SimpleItem:
            def __str__(self) -> str:
                return "String representation"

        item = SimpleItem()

        result = BaseMCPTool._format_contents([item])

        assert result == "String representation"


class TestAbstractRunMethod:
    """Test the abstract run method contract."""

    def test_run_method_is_defined_in_base_class(self):
        """Test that BaseMCPTool defines a run method."""
        # Check that run method exists
        assert hasattr(BaseMCPTool, "run")
        assert callable(BaseMCPTool.run)

    def test_run_method_has_correct_signature(self):
        """Test that run method has the expected signature."""
        import inspect

        sig = inspect.signature(BaseMCPTool.run)
        params = list(sig.parameters.keys())

        # Should have self, query, and **kwargs
        assert "self" in params
        assert "query" in params
        assert "kwargs" in params

    @pytest.mark.asyncio
    async def test_concrete_implementation_works(self):
        """Test that a concrete implementation can be instantiated and run."""
        tool = ConcreteMCPTool(
            name="test_tool",
            url="https://example.com",
            description="Test description",
        )

        tool.connect = AsyncMock()
        tool.call_tool = AsyncMock(return_value=[])
        tool.disconnect = AsyncMock()

        result = await tool.run("test query")

        assert result == "Empty response"
        tool.connect.assert_called_once()
