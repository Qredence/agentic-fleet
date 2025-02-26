"""Test configuration and fixtures."""
import os
from typing import Generator

import pytest
from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def setup_test_env() -> Generator:
    """Set up test environment variables."""
    # Store current environment
    old_environ = dict(os.environ)

    # Load test environment
    load_dotenv(".env.test", override=True)

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def mock_user_session():
    """Mock for chainlit's user_session with a custom get/set behavior."""
    session_data = {}
    
    # Create a mock for the user_session object
    user_session_mock = MagicMock()
    
    # Configure the get method
    def mock_get(key, default=None):
        return session_data.get(key, default)
    
    # Configure the set method
    def mock_set(key, value):
        session_data[key] = value
    
    # Assign the mock methods to the mock object
    user_session_mock.get.side_effect = mock_get
    user_session_mock.set.side_effect = mock_set
    
    # Patch the user_session object
    with patch('chainlit.user_session.user_session', user_session_mock):
        yield session_data


@pytest.fixture
def mock_chainlit_elements():
    """Mock for chainlit UI elements."""
    text_mock = MagicMock()
    text_mock.send = AsyncMock()
    
    message_mock = MagicMock()
    message_mock.send = AsyncMock()
    
    task_mock = MagicMock()
    task_mock.add_task = AsyncMock()
    task_mock.update_task = AsyncMock()
    
    with patch('chainlit.Text', return_value=text_mock), \
         patch('chainlit.Message', return_value=message_mock), \
         patch('chainlit.TaskList', return_value=task_mock):
        yield {
            'text': text_mock,
            'message': message_mock,
            'task_list': task_mock
        }


@pytest.fixture
def mock_settings_components():
    """Mock for chainlit settings components."""
    settings_mock = MagicMock()
    select_mock = MagicMock()
    slider_mock = MagicMock()
    switch_mock = MagicMock()
    
    with patch('chainlit.ChatSettings', return_value=settings_mock), \
         patch('chainlit.Select', return_value=select_mock), \
         patch('chainlit.Slider', return_value=slider_mock), \
         patch('chainlit.Switch', return_value=switch_mock):
        yield {
            'settings': settings_mock,
            'select': select_mock,
            'slider': slider_mock,
            'switch': switch_mock
        }


@pytest.fixture
def mock_openai_client():
    """Mock for Azure OpenAI client."""
    client_mock = MagicMock()
    client_mock.model = "gpt-4o-mini-2024-07-18"
    client_mock.streaming = True
    client_mock.model_info = {"vision": True, "function_calling": True}
    
    with patch('agentic_fleet.models.client_factory.AzureOpenAIChatCompletionClient', 
               return_value=client_mock):
        yield client_mock


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        'AZURE_OPENAI_ENDPOINT': 'https://test-endpoint.com',
        'AZURE_OPENAI_API_KEY': 'test-key',
        'AZURE_OPENAI_API_VERSION': '2024-08-01'
    }
    
    with patch.dict('os.environ', env_vars, clear=False):
        yield
