from unittest.mock import patch

import pytest
from agent_framework import ChatMessage

from agentic_fleet.tools.azure_search_provider import AzureAISearchContextProvider


@pytest.fixture
def mock_search_client():
    with patch("agentic_fleet.tools.azure_search_provider.SearchClient") as mock:
        yield mock


@pytest.fixture
def provider(mock_search_client):
    return AzureAISearchContextProvider(
        endpoint="https://test.search.windows.net", index_name="test-index", api_key="test-key"
    )


@pytest.mark.asyncio
async def test_invoking_with_results(provider, mock_search_client):
    # Setup mock results
    mock_client_instance = mock_search_client.return_value
    mock_client_instance.search.return_value = [
        {"content": "This is a test document.", "source": "doc1"},
        {"content": "Another document.", "source": "doc2"},
    ]

    # Create a message
    message = ChatMessage(role="user", text="test query")

    # Invoke provider
    context = await provider.invoking([message])

    # Verify search was called
    mock_client_instance.search.assert_called_once_with(search_text="test query", top=3)

    # Verify context
    assert context.instructions is not None
    assert "This is a test document." in context.instructions
    assert "Another document." in context.instructions
    assert "Source: doc1" in context.instructions


@pytest.mark.asyncio
async def test_invoking_no_results(provider, mock_search_client):
    # Setup mock results
    mock_client_instance = mock_search_client.return_value
    mock_client_instance.search.return_value = []

    # Create a message
    message = ChatMessage(role="user", text="test query")

    # Invoke provider
    context = await provider.invoking([message])

    # Verify context is empty
    assert context.instructions is None


@pytest.mark.asyncio
async def test_invoking_no_client():
    # Create provider without credentials
    with patch.dict("os.environ", {}, clear=True):
        provider = AzureAISearchContextProvider()

    # Create a message
    message = ChatMessage(role="user", text="test query")

    # Invoke provider
    context = await provider.invoking([message])

    # Verify context is empty
    assert context.instructions is None
