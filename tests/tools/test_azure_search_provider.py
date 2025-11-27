from unittest.mock import patch

import pytest
from agent_framework._types import ChatMessage

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


@pytest.fixture
def provider_with_semantic(mock_search_client):
    return AzureAISearchContextProvider(
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        api_key="test-key",
        semantic_configuration_name="my-semantic-config",
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


@pytest.mark.asyncio
async def test_invoking_with_semantic_search(provider_with_semantic, mock_search_client):
    """Test that semantic search configuration is used when provided."""
    # Setup mock results
    mock_client_instance = mock_search_client.return_value
    mock_client_instance.search.return_value = [
        {"content": "Semantic search result.", "source": "semantic-doc"},
    ]

    # Create a message
    message = ChatMessage(role="user", text="semantic query")

    # Invoke provider
    context = await provider_with_semantic.invoking([message])

    # Verify search was called with semantic configuration
    mock_client_instance.search.assert_called_once_with(
        search_text="semantic query",
        top=3,
        query_type="semantic",
        semantic_configuration_name="my-semantic-config",
    )

    # Verify context
    assert context.instructions is not None
    assert "Semantic search result." in context.instructions


@pytest.mark.asyncio
async def test_invoking_with_search_exception(provider, mock_search_client):
    """Test error handling when search client raises an exception."""
    # Setup mock to raise an exception
    mock_client_instance = mock_search_client.return_value
    mock_client_instance.search.side_effect = Exception("Search service unavailable")

    # Create a message
    message = ChatMessage(role="user", text="test query")

    # Invoke provider - should not raise, but return empty context
    context = await provider.invoking([message])

    # Verify context is empty (graceful degradation)
    assert context.instructions is None


@pytest.mark.asyncio
async def test_invoking_with_alternative_field_names(provider, mock_search_client):
    """Test that alternative field names (text, description, url, title) are handled."""
    # Setup mock results with alternative field names
    mock_client_instance = mock_search_client.return_value
    mock_client_instance.search.return_value = [
        {"text": "Document using text field.", "url": "https://example.com/doc1"},
        {"description": "Document using description field.", "title": "Doc Title"},
    ]

    # Create a message
    message = ChatMessage(role="user", text="test query")

    # Invoke provider
    context = await provider.invoking([message])

    # Verify context contains both documents with their respective fields
    assert context.instructions is not None
    assert "Document using text field." in context.instructions
    assert "Document using description field." in context.instructions
    assert "Source: https://example.com/doc1" in context.instructions
    assert "Source: Doc Title" in context.instructions


@pytest.mark.asyncio
async def test_invoking_with_single_message(provider, mock_search_client):
    """Test that a single ChatMessage (not a list) is handled correctly."""
    # Setup mock results
    mock_client_instance = mock_search_client.return_value
    mock_client_instance.search.return_value = [
        {"content": "Single message result.", "source": "single-doc"},
    ]

    # Create a single message (not in a list)
    message = ChatMessage(role="user", text="single message query")

    # Invoke provider with single message
    context = await provider.invoking(message)

    # Verify search was called with the message text
    mock_client_instance.search.assert_called_once_with(search_text="single message query", top=3)

    # Verify context
    assert context.instructions is not None
    assert "Single message result." in context.instructions


@pytest.mark.asyncio
async def test_invoking_with_empty_messages(provider, mock_search_client):
    """Test that empty messages list returns empty context."""
    # Create empty messages list
    messages = []

    # Invoke provider
    context = await provider.invoking(messages)

    # Verify context is empty
    assert context.instructions is None

    # Verify search was not called
    mock_client_instance = mock_search_client.return_value
    mock_client_instance.search.assert_not_called()
