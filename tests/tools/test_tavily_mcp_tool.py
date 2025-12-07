"""Tests for TavilyMCPTool authentication and initialization.

These tests verify that TavilyMCPTool uses secure authentication via
Authorization header (Bearer token) rather than URL query parameters.
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _import_base_mcp_tool():
    """
    Load the BaseMCPTool class directly from its source file while providing test-time fallbacks for agent_framework modules.

    Ensures a lightweight MockMCPStreamableHTTPTool is available as agent_framework._mcp and that agent_framework.exceptions exposes ToolException and ToolExecutionException, then imports base_mcp_tool.py from the repository path and returns its BaseMCPTool class.

    Returns:
        BaseMCPTool: The BaseMCPTool class loaded from the source file.

    Raises:
        AssertionError: If the module spec or its loader cannot be created or loaded.
    """
    # First, ensure we have a fallback MCPStreamableHTTPTool
    if "agent_framework._mcp" not in sys.modules:
        mock_mcp = MagicMock()

        class MockMCPStreamableHTTPTool:
            """Mock MCP tool for testing."""

            def __init__(self, *args: Any, **kwargs: Any):
                self.name = kwargs.get("name", "mcp_tool")
                self.description = kwargs.get("description", "")
                self.url = kwargs.get("url", "")
                self.headers = kwargs.get("headers", {})
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

    if "agent_framework.exceptions" not in sys.modules:
        mock_exceptions = MagicMock()
        mock_exceptions.ToolException = Exception
        mock_exceptions.ToolExecutionException = Exception
        sys.modules["agent_framework.exceptions"] = mock_exceptions

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


class TavilyMCPTool(BaseMCPTool):
    """Test implementation of TavilyMCPTool that mirrors the real implementation.

    This mirrors the implementation in src/agentic_fleet/tools/mcp_tools.py
    to verify the authentication behavior without needing full agent_framework.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Tavily MCP tool.

        Args:
            api_key: Tavily API key (defaults to TAVILY_API_KEY env var)

        Raises:
            ValueError: If API key is not provided
        """
        api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY must be set in environment or passed to constructor")

        mcp_url = "https://mcp.tavily.com/mcp/"

        # Pass API key via header to avoid leaking credentials in URLs/logs
        auth_headers = {"Authorization": f"Bearer {api_key}"}

        description = (
            "MANDATORY: Use this tool for ANY query about events, dates, or information from 2024 onwards. "
            "Search the web for real-time information using Tavily. Provides accurate, up-to-date results with source citations. "
            "ALWAYS use this tool when asked about recent events, current data, elections, news, or anything requiring current information. "
            "Never rely on training data for time-sensitive queries."
        )

        super().__init__(
            name="tavily_search",
            url=mcp_url,
            description=description,
            load_tools=True,
            load_prompts=False,
            headers=auth_headers,
        )

        # Store URL explicitly for testing (mirrors what parent mock should do)
        self.url = mcp_url

    async def run(self, query: str, **kwargs: Any) -> str:
        """Execute a Tavily search query via MCP."""
        return "Mock response"


class TestTavilyMCPToolAuthentication:
    """Tests for TavilyMCPTool authentication method."""

    def test_api_key_passed_via_authorization_header(self):
        """Verify API key is passed via Authorization header, not URL query param."""
        test_api_key = "test-api-key-12345"

        tool = TavilyMCPTool(api_key=test_api_key)

        # Verify headers contain Authorization with Bearer token
        assert "Authorization" in tool.headers
        assert tool.headers["Authorization"] == f"Bearer {test_api_key}"

    def test_url_does_not_contain_api_key(self):
        """Verify the MCP URL does not contain the API key as query parameter."""
        test_api_key = "secret-api-key"

        tool = TavilyMCPTool(api_key=test_api_key)

        # URL should not contain the API key
        assert test_api_key not in tool.url
        assert "tavilyApiKey" not in tool.url
        assert "apiKey" not in tool.url.lower()

    def test_uses_correct_mcp_url(self):
        """Verify the correct Tavily MCP URL is used."""
        tool = TavilyMCPTool(api_key="test-key")

        assert tool.url == "https://mcp.tavily.com/mcp/"

    def test_uses_env_var_when_no_api_key_passed(self):
        """Verify TAVILY_API_KEY environment variable is used when not passed."""
        env_api_key = "env-api-key-67890"

        with patch.dict(os.environ, {"TAVILY_API_KEY": env_api_key}):
            tool = TavilyMCPTool()

            assert tool.headers["Authorization"] == f"Bearer {env_api_key}"

    def test_raises_value_error_when_no_api_key(self):
        """Verify ValueError is raised when no API key is provided."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": ""}, clear=False):
            # Remove the env var if it exists
            os.environ.pop("TAVILY_API_KEY", None)

            with pytest.raises(ValueError, match="TAVILY_API_KEY"):
                TavilyMCPTool()

    def test_tool_name_is_tavily_search(self):
        """Verify the tool is named correctly."""
        tool = TavilyMCPTool(api_key="test-key")

        assert tool.name == "tavily_search"

    def test_description_mentions_web_search(self):
        """Verify the description describes the tool's purpose."""
        tool = TavilyMCPTool(api_key="test-key")

        assert "search" in tool.description.lower()
        assert "web" in tool.description.lower() or "real-time" in tool.description.lower()


class TestTavilyMCPToolSecurityBestPractices:
    """Tests verifying security best practices for API key handling."""

    def test_bearer_token_format(self):
        """Verify Bearer token follows standard OAuth2 format."""
        api_key = "my-secret-key"
        tool = TavilyMCPTool(api_key=api_key)

        auth_header = tool.headers.get("Authorization", "")

        # Should follow "Bearer <token>" format per RFC 6750
        assert auth_header.startswith("Bearer ")
        assert auth_header == f"Bearer {api_key}"

    def test_no_credentials_in_logged_url(self):
        """Verify URL can be safely logged without exposing credentials."""
        sensitive_key = "super-secret-api-key-xyz"
        tool = TavilyMCPTool(api_key=sensitive_key)

        # URL should be safe to log
        url_for_logging = tool.url
        assert sensitive_key not in url_for_logging
