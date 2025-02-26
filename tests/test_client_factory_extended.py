"""Extended tests for the client factory module."""

import pytest
from unittest.mock import MagicMock, patch
import os

from agentic_fleet.models.client_factory import create_client, get_cached_client


@pytest.fixture
def mock_azure_env_vars():
    """Set up mock Azure environment variables."""
    env_vars = {
        'AZURE_OPENAI_ENDPOINT': 'https://test-endpoint.com',
        'AZURE_OPENAI_API_KEY': 'test-key',
        'AZURE_OPENAI_API_VERSION': '2024-08-01'
    }
    
    with patch.dict('os.environ', env_vars, clear=False):
        yield


def test_create_client_with_required_params(mock_azure_env_vars):
    """Test creating a client with only required parameters."""
    with patch('agentic_fleet.models.client_factory.AzureOpenAIChatCompletionClient') as mock_client_class:
        mock_client = mock_client_class.return_value
        
        # Call the function
        client = create_client(model_name="gpt-4o-mini")
        
        # Verify client was created with correct parameters
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args.kwargs
        
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["endpoint"] == "https://test-endpoint.com"
        assert call_kwargs["api_version"] == "2024-08-01"
        
        # Default values
        assert call_kwargs["streaming"] is False
        assert call_kwargs["timeout"] == 60
        
        # Verify the returned client is correct
        assert client == mock_client


def test_create_client_with_all_params(mock_azure_env_vars):
    """Test creating a client with all parameters specified."""
    with patch('agentic_fleet.models.client_factory.AzureOpenAIChatCompletionClient') as mock_client_class:
        mock_client = mock_client_class.return_value
        
        # Call the function with all parameters
        client = create_client(
            model_name="gpt-4o-mini",
            streaming=True,
            vision=True,
            connection_pool_size=5,
            request_timeout=30
        )
        
        # Verify client was created with correct parameters
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args.kwargs
        
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["endpoint"] == "https://test-endpoint.com"
        assert call_kwargs["api_version"] == "2024-08-01"
        assert call_kwargs["streaming"] is True
        assert call_kwargs["timeout"] == 30
        assert call_kwargs["connection_pool_size"] == 5
        
        # Verify the returned client is correct
        assert client == mock_client


def test_create_client_missing_env_vars():
    """Test that create_client raises an error when environment variables are missing."""
    # Remove required environment variables
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            create_client(model_name="gpt-4o-mini")
        
        # Verify the error message
        assert "AZURE_OPENAI_ENDPOINT" in str(excinfo.value)
        assert "AZURE_OPENAI_API_KEY" in str(excinfo.value)


def test_get_cached_client(mock_azure_env_vars):
    """Test that get_cached_client caches clients correctly."""
    with patch('agentic_fleet.models.client_factory.AzureOpenAIChatCompletionClient') as mock_client_class:
        # First call should create a new client
        client1 = get_cached_client(model_name="gpt-4o-mini")
        assert mock_client_class.call_count == 1
        
        # Second call with same parameters should reuse the cached client
        client2 = get_cached_client(model_name="gpt-4o-mini")
        assert mock_client_class.call_count == 1  # Still 1, not 2
        assert client1 == client2
        
        # Call with different parameters should create a new client
        client3 = get_cached_client(model_name="gpt-4o", streaming=True)
        assert mock_client_class.call_count == 2
        assert client1 != client3


def test_model_info_construction(mock_azure_env_vars):
    """Test that model_info is correctly constructed based on parameters."""
    with patch('agentic_fleet.models.client_factory.AzureOpenAIChatCompletionClient') as mock_client_class:
        mock_client = mock_client_class.return_value
        
        # Call with vision=True
        client1 = create_client(model_name="gpt-4o-mini", vision=True)
        assert hasattr(client1, "model_info")
        assert client1.model_info["vision"] is True
        
        # Call with vision=False
        mock_client_class.reset_mock()
        client2 = create_client(model_name="gpt-4o-mini", vision=False)
        assert hasattr(client2, "model_info")
        assert client2.model_info["vision"] is False
        
        # Verify function_calling is always True for now
        assert client1.model_info["function_calling"] is True
        assert client2.model_info["function_calling"] is True 