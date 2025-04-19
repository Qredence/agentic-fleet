"""Unit tests for the chainlit application."""

import pytest
import asyncio
import chainlit as cl
from unittest.mock import AsyncMock, MagicMock, patch
from chainlit.context import ChainlitContext, context_var
from chainlit.session import Session
from chainlit.user_session import UserSession
from agentic_fleet.chainlit_app import (
    AppContext,
    start_chat,
    get_profile_metadata,
    send_welcome_message,
    message_handler,
    handle_settings_update,
    on_action_reset,
    on_action_list_mcp,
    on_chat_stop
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def app_context():
    """Fixture for app context."""
    context = AppContext()
    context.client = MagicMock()
    context.app_manager = MagicMock()
    context.app_manager.start = AsyncMock()
    context.app_manager.shutdown = AsyncMock()
    return context

@pytest.fixture
def mock_chainlit_context():
    """Mock Chainlit context."""
    session = Session(
        thread_id="test_thread",
        user_env={},
        user_infos={"username": "test_user"},
        user_settings={},
    )
    context = ChainlitContext(session=session)
    token = context_var.set(context)
    yield context
    context_var.reset(token)

@pytest.fixture
def mock_cl_session():
    """Mock Chainlit user session."""
    session = UserSession()
    with patch('chainlit.user_session', session):
        yield session

@pytest.mark.asyncio
async def test_get_profile_metadata(mock_chainlit_context):
    """Test get_profile_metadata function."""
    with patch('agentic_fleet.config.llm_config_manager.get_profile_config') as mock_get_config:
        mock_get_config.return_value = {
            "description": "Test Description",
            "icon": "test_icon.svg"
        }
        metadata = await mock_get_config("test_profile")
        assert metadata["description"] == "Test Description"
        assert metadata["icon"] == "test_icon.svg"

@pytest.mark.asyncio
async def test_send_welcome_message(mock_chainlit_context):
    """Test send_welcome_message function."""
    profile_name = "test_profile"
    model_name = "test_model"
    settings = {"temperature": 0.7}
    profile_desc = "Test Profile Description"

    with patch('chainlit.Message') as mock_message, \
         patch('chainlit.user_session.get', return_value="test_icon.svg"):
        mock_message.return_value.send = AsyncMock()
        await send_welcome_message(profile_name, model_name, settings, profile_desc)
        mock_message.assert_called_once()

@pytest.mark.asyncio
async def test_on_chat_stop(mock_chainlit_context):
    """Test chat stop handler."""
    with patch('agentic_fleet.chainlit_app.app_context') as mock_app_context:
        mock_app_context.app_manager = MagicMock()
        mock_app_context.app_manager.stop = AsyncMock()
        await cl.on_chat_stop()
        mock_app_context.app_manager.stop.assert_called_once()

@pytest.mark.asyncio
async def test_message_handler(mock_chainlit_context):
    """Test message handler function."""
    mock_message = MagicMock()

    with patch('chainlit.user_session.get', return_value="default"), \
         patch('agentic_fleet.ui.message_handler.handle_chat_message') as mock_handler:
        mock_handler.return_value = AsyncMock()
        await cl.on_message(mock_message)
        mock_handler.assert_called_once_with(mock_message)

@pytest.mark.asyncio
async def test_handle_settings_update(mock_chainlit_context):
    """Test settings update handler."""
    mock_settings = {"temperature": 0.7}
    with patch('chainlit.user_session.set') as mock_set:
        await cl.on_settings_update(mock_settings)
        mock_set.assert_called_once_with("settings", mock_settings)

@pytest.mark.asyncio
async def test_start_chat_success(app_context, mock_cl_session, mock_chainlit_context):
    """Test successful chat start."""
    mock_cl_session.get.return_value = "default"

    with patch('agentic_fleet.chainlit_app.app_context', app_context), \
         patch('agentic_fleet.config.config_manager.load_all') as mock_load_all, \
         patch('agentic_fleet.config.config_manager.validate_environment') as mock_validate, \
         patch('agentic_fleet.config.config_manager.get_environment_settings') as mock_get_env, \
         patch('agentic_fleet.core.agents.team.initialize_default_agents') as mock_init_agents, \
         patch('agentic_fleet.ui.task_manager.initialize_task_list') as mock_init_tasks, \
         patch('agentic_fleet.chainlit_app.send_welcome_message') as mock_welcome, \
         patch('chainlit.user_session.set'):

        mock_validate.return_value = None
        mock_get_env.return_value = MagicMock(debug=False, log_level="INFO")
        mock_init_agents.return_value = [MagicMock()]
        mock_init_tasks.return_value = None
        mock_welcome.return_value = AsyncMock()

        await start_chat()
        mock_load_all.assert_called_once()
        mock_validate.assert_called_once()
        mock_welcome.assert_called_once()

@pytest.mark.asyncio
async def test_start_chat_failure(app_context, mock_cl_session, mock_chainlit_context):
    """Test chat start with configuration error."""
    mock_cl_session.get.return_value = "default"

    with patch('agentic_fleet.chainlit_app.app_context', app_context), \
         patch('agentic_fleet.config.config_manager.load_all') as mock_load_all, \
         patch('chainlit.Message') as mock_message:
        mock_load_all.side_effect = Exception("Test error")
        mock_message.return_value.send = AsyncMock()

        await start_chat()
        mock_message.assert_called_once()

@pytest.mark.asyncio
async def test_on_action_reset(mock_chainlit_context):
    """Test reset action callback."""
    mock_action = MagicMock()

    with patch('agentic_fleet.ui.message_handler.on_reset') as mock_reset, \
         patch('chainlit.Message') as mock_message:
        mock_message.return_value.send = AsyncMock()
        mock_reset.return_value = None
        await on_action_reset(mock_action)
        mock_reset.assert_called_once_with(mock_action)

@pytest.mark.asyncio
async def test_on_action_list_mcp_success(mock_chainlit_context):
    """Test list MCP tools action callback success."""
    mock_action = MagicMock()
    mock_servers = ["server1", "server2"]

    with patch('agentic_fleet.ui.components.mcp_panel.list_available_mcps') as mock_list_mcps, \
         patch('chainlit.user_session.set') as mock_set, \
         patch('chainlit.Message') as mock_message:
        mock_message.return_value.send = AsyncMock()
        mock_list_mcps.return_value = mock_servers
        await on_action_list_mcp(mock_action)
        mock_set.assert_called_once_with("mcp_servers", mock_servers)

@pytest.mark.asyncio
async def test_on_action_list_mcp_failure(mock_chainlit_context):
    """Test list MCP tools action callback failure."""
    mock_action = MagicMock()

    with patch('agentic_fleet.ui.components.mcp_panel.list_available_mcps') as mock_list_mcps, \
         patch('chainlit.Message') as mock_message:
        mock_message.return_value.send = AsyncMock()
        mock_list_mcps.side_effect = Exception("Test error")
        await on_action_list_mcp(mock_action)
        mock_message.assert_called_once() 