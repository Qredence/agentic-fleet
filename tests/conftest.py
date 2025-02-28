"""Test configuration and fixtures."""

import os
from typing import Generator

import pytest
from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock, patch

from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
import chainlit
import contextlib


@pytest.fixture(autouse=True)
def setup_test_env() -> Generator:
    """Set up test environment variables."""
    # Store current environment
    old_environ = dict(os.environ)

    # Load test environment
    load_dotenv(".env.test", override=True)

    # Ensure Azure OpenAI environment variables are set
    os.environ.setdefault('AZURE_OPENAI_ENDPOINT', 'https://test.openai.azure.com')
    os.environ.setdefault('AZURE_OPENAI_API_KEY', 'test-api-key')
    os.environ.setdefault('AZURE_OPENAI_API_VERSION', '2024-02-01')

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def mock_chainlit_context(monkeypatch):
    """Mock the Chainlit context."""
    # Create a mock context session
    mock_session = MagicMock()
    mock_session.thread_id = "test_thread"

    # Create a mock context
    mock_context = MagicMock()
    mock_context.session = mock_session

    # Create a mock context_var that returns the mock context
    context_var_mock = MagicMock()
    context_var_mock.get.return_value = mock_context

    # Patch the Chainlit context methods
    def mock_get_context():
        return mock_context

    # Patch the context methods and variables
    monkeypatch.setattr(chainlit.context, 'get_context', mock_get_context)
    monkeypatch.setattr(chainlit.context, 'session', mock_session)
    monkeypatch.setattr(chainlit.context, 'context_var', context_var_mock)

    # Create a context manager that returns the mock context
    @contextlib.contextmanager
    def mock_context_manager():
        yield mock_context

    monkeypatch.setattr(chainlit.context, 'context', mock_context_manager)

    return mock_context


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
    with patch("chainlit.user_session.user_session", user_session_mock):
        yield session_data


@pytest.fixture
def mock_azure_client():
    """Create a mock Azure OpenAI client."""
    mock_client = AsyncMock(spec=AzureOpenAIChatCompletionClient)
    return mock_client


@pytest.fixture
def mock_code_executor():
    """Create a mock code executor."""
    mock_executor = AsyncMock(spec=LocalCommandLineCodeExecutor)
    return mock_executor


@pytest.fixture
def mock_chainlit_message():
    """Create a mock Chainlit message."""
    mock_message = AsyncMock()
    mock_message.content = "Test message"
    return mock_message


@pytest.fixture
def mock_web_surfer(monkeypatch):
    """Mock the WebSurfer initialization."""
    # Create a mock MultimodalWebSurfer
    mock_web_surfer = MagicMock()
    mock_web_surfer.name = "WebSurfer"

    # Patch the MultimodalWebSurfer import
    monkeypatch.setattr(
        'autogen_ext.agents.web_surfer._multimodal_web_surfer.MultimodalWebSurfer',
        MagicMock(return_value=mock_web_surfer)
    )

    return mock_web_surfer


@pytest.fixture
def mock_magentic_one_team():
    """Mock the MagenticOneGroupChat team."""
    mock_team = AsyncMock()
    mock_team.run.return_value = "Task completed"
    mock_team.run_stream.return_value = AsyncMock().__aiter__.return_value = [
        "Response chunk 1",
        "Response chunk 2"
    ]
    return mock_team


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

    with (
        patch("chainlit.Text", return_value=text_mock),
        patch("chainlit.Message", return_value=message_mock),
        patch("chainlit.TaskList", return_value=task_mock),
    ):
        yield {
            "Text": MagicMock(return_value=text_mock),
            "text": text_mock,
            "message": message_mock,
            "task_list": task_mock,
        }


@pytest.fixture
def mock_settings_components():
    """Mock for chainlit settings components."""
    settings_mock = MagicMock()
    select_mock = MagicMock()
    slider_mock = MagicMock()
    switch_mock = MagicMock()

    with (
        patch("chainlit.ChatSettings", return_value=settings_mock),
        patch("chainlit.Select", return_value=select_mock),
        patch("chainlit.Slider", return_value=slider_mock),
        patch("chainlit.Switch", return_value=switch_mock),
    ):
        yield {
            "settings": settings_mock,
            "select": select_mock,
            "slider": slider_mock,
            "switch": switch_mock,
        }


@pytest.fixture
def mock_openai_client():
    """Mock for Azure OpenAI client."""
    client_mock = MagicMock()
    client_mock.model = "gpt-4o-mini-2024-07-18"
    client_mock.streaming = True
    client_mock.model_info = {"vision": True, "function_calling": True}

    with patch(
        "agentic_fleet.models.client_factory.AzureOpenAIChatCompletionClient",
        return_value=client_mock,
    ):
        yield client_mock


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "AZURE_OPENAI_ENDPOINT": "https://test-endpoint.com",
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_API_VERSION": "2024-08-01",
    }

    with patch.dict("os.environ", env_vars, clear=False):
        yield
