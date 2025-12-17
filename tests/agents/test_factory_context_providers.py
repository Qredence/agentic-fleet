from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.agents.coordinator import AgentFactory
from agentic_fleet.tools.azure_search_provider import AzureAISearchContextProvider


@pytest.fixture
def mock_openai_client():
    return MagicMock()


@pytest.fixture
def factory(mock_openai_client):
    return AgentFactory(openai_client=mock_openai_client)


def test_resolve_context_providers(factory):
    # Mock environment variables for Azure Search to avoid warning/error during instantiation
    with patch.dict(
        "os.environ",
        {
            "AZURE_SEARCH_ENDPOINT": "https://test.search.windows.net",
            "AZURE_SEARCH_INDEX": "test-index",
            "AZURE_SEARCH_KEY": "test-key",
        },
    ):
        providers = factory._resolve_context_providers(["AzureAISearchContextProvider"])
        assert len(providers) == 1
        assert isinstance(providers[0], AzureAISearchContextProvider)


def test_resolve_context_providers_invalid(factory):
    providers = factory._resolve_context_providers(["InvalidProvider"])
    assert len(providers) == 0


@patch("agentic_fleet.agents.coordinator.OpenAIResponsesClient")
def test_create_agent_with_context_provider(mock_client_cls, factory):
    config = {"model": "gpt-4.1-mini", "context_providers": ["AzureAISearchContextProvider"]}

    with patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test-key",
            "AZURE_SEARCH_ENDPOINT": "https://test.search.windows.net",
            "AZURE_SEARCH_INDEX": "test-index",
            "AZURE_SEARCH_KEY": "test-key",
        },
    ):
        agent = factory.create_agent("test_agent", config)

    assert agent is not None
    assert agent.name == "Test_agentAgent"
