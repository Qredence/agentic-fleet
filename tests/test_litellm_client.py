"""Tests for LiteLLM Client Integration

This module tests the LiteLLMClient implementation and its integration
with the agent factory system.
"""

import pytest

from agenticfleet.core.litellm_client import LiteLLMClient


def test_litellm_client_import() -> None:
    """Test that LiteLLMClient can be imported."""
    assert LiteLLMClient is not None


def test_litellm_client_initialization() -> None:
    """Test LiteLLMClient initialization with various parameters."""
    # Basic initialization
    client = LiteLLMClient(model="gpt-4o-mini")
    assert client is not None
    assert client.additional_properties["model"] == "gpt-4o-mini"

    # Initialization with all parameters
    client = LiteLLMClient(
        model="gpt-4o-mini",
        api_key="test-key",
        base_url="https://api.example.com",
        temperature=0.7,
        max_tokens=1000,
        timeout=30.0,
    )
    assert client.additional_properties["model"] == "gpt-4o-mini"
    assert client.additional_properties["base_url"] == "https://api.example.com"
    assert client.additional_properties["temperature"] == 0.7
    assert client.additional_properties["max_tokens"] == 1000
    assert client.additional_properties["timeout"] == 30.0


def test_litellm_client_anthropic_model() -> None:
    """Test LiteLLMClient with Anthropic model identifier."""
    client = LiteLLMClient(model="anthropic/claude-3-5-sonnet-20241022")
    assert client is not None
    assert "anthropic" in client.additional_properties["model"]


def test_litellm_client_azure_model() -> None:
    """Test LiteLLMClient with Azure model identifier."""
    client = LiteLLMClient(model="azure/gpt-4o")
    assert client is not None
    assert "azure" in client.additional_properties["model"]


def test_create_chat_client_with_litellm() -> None:
    """Test create_chat_client factory function with LiteLLM."""
    from agenticfleet.core.openai import create_chat_client

    # Test with use_litellm=True
    client = create_chat_client(
        model="gpt-4o-mini",
        use_litellm=True,
        api_key="test-key",
        temperature=0.5,
    )
    assert isinstance(client, LiteLLMClient)
    assert client.additional_properties["model"] == "gpt-4o-mini"
    assert client.additional_properties["temperature"] == 0.5


def test_create_chat_client_with_openai() -> None:
    """Test create_chat_client factory function with OpenAI client."""
    from agenticfleet.core.openai import create_chat_client

    try:
        from agent_framework.openai import OpenAIResponsesClient
    except ImportError:
        pytest.skip("agent_framework not available")

    # Test with use_litellm=False
    client = create_chat_client(
        model="gpt-4o-mini",
        use_litellm=False,
    )
    assert isinstance(client, OpenAIResponsesClient)


def test_litellm_settings_integration() -> None:
    """Test that LiteLLM settings are properly loaded."""
    from agenticfleet.config import settings

    # Check that LiteLLM settings exist
    assert hasattr(settings, "use_litellm")
    assert hasattr(settings, "litellm_model")
    assert hasattr(settings, "litellm_api_key")
    assert hasattr(settings, "litellm_base_url")
    assert hasattr(settings, "litellm_timeout")

    # Check default values
    assert isinstance(settings.use_litellm, bool)
    assert isinstance(settings.litellm_timeout, float)


def test_agent_factory_with_litellm_disabled() -> None:
    """Test agent factories work with LiteLLM disabled (default behavior)."""
    from agenticfleet.agents.researcher import create_researcher_agent
    from agenticfleet.config import settings

    # Ensure LiteLLM is disabled
    original_use_litellm = settings.use_litellm
    try:
        settings.use_litellm = False

        # Create agent - should use OpenAI client
        agent = create_researcher_agent()
        assert agent is not None
        assert agent.name == "researcher"
    finally:
        settings.use_litellm = original_use_litellm


@pytest.mark.skipif(
    not hasattr(__import__("agenticfleet.config", fromlist=["settings"]).settings, "use_litellm"),
    reason="LiteLLM support not configured",
)
def test_agent_factory_with_litellm_enabled() -> None:
    """Test agent factories work with LiteLLM enabled."""
    from agenticfleet.agents.coder import create_coder_agent
    from agenticfleet.config import settings

    # Enable LiteLLM temporarily
    original_use_litellm = settings.use_litellm
    original_litellm_model = settings.litellm_model
    try:
        settings.use_litellm = True
        settings.litellm_model = "gpt-4o-mini"

        # Create agent - should use LiteLLM client
        agent = create_coder_agent()
        assert agent is not None
        assert agent.name == "coder"
    finally:
        settings.use_litellm = original_use_litellm
        settings.litellm_model = original_litellm_model


def test_litellm_client_convert_messages() -> None:
    """Test message conversion between Agent Framework and LiteLLM formats."""
    from agent_framework._types import ChatMessage, TextContent

    client = LiteLLMClient(model="gpt-4o-mini")

    # Test simple text message
    messages = [ChatMessage(role="user", text="Hello")]
    litellm_messages = client._convert_messages_to_litellm(messages)
    assert len(litellm_messages) == 1
    assert litellm_messages[0]["role"] == "user"
    assert litellm_messages[0]["content"] == "Hello"

    # Test message with contents
    messages = [
        ChatMessage(
            role="assistant",
            contents=[
                TextContent(text="Part 1"),
                TextContent(text="Part 2"),
            ],
        )
    ]
    litellm_messages = client._convert_messages_to_litellm(messages)
    assert len(litellm_messages) == 1
    assert litellm_messages[0]["role"] == "assistant"
    assert "Part 1" in litellm_messages[0]["content"]
    assert "Part 2" in litellm_messages[0]["content"]
