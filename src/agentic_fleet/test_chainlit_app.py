import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
from pathlib import Path
from agentic_fleet.core.application.manager import ApplicationManager, ApplicationConfig

"""
Unit tests for the chainlit_app.py module.
"""

# Import the module to test
import agentic_fleet.chainlit_app as chainlit_app


@pytest.fixture
def mock_chainlit():
    """Mock all chainlit dependencies."""
    with patch("agentic_fleet.chainlit_app.cl") as mock_cl:
        # Setup user_session with get and set methods
        mock_user_session = MagicMock()
        mock_user_session.get = MagicMock(return_value=None)
        mock_user_session.set = MagicMock()
        mock_cl.user_session = mock_user_session

        # Mock Message class and methods
        mock_message = MagicMock()
        mock_message.send = AsyncMock()
        mock_cl.Message.return_value = mock_message

        # Mock Action class
        mock_cl.Action = MagicMock()

        yield mock_cl


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager."""
    with patch("agentic_fleet.chainlit_app.config_manager") as mock_config:
        mock_config.load_all = MagicMock()
        mock_config.validate_environment = MagicMock(return_value=None)
        mock_config.get_environment_settings = MagicMock(return_value={"debug": False, "log_level": "INFO"})
        yield mock_config


@pytest.fixture
def mock_client():
    """Mock the client factory."""
    with patch("agentic_fleet.chainlit_app.get_cached_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_app_manager():
    """Mock application manager."""
    with patch("agentic_fleet.chainlit_app.ApplicationManager") as mock_manager_cls:
        mock_manager = MagicMock(spec=ApplicationManager)
        mock_manager.start = AsyncMock()
        mock_manager.shutdown = AsyncMock()
        mock_manager_cls.return_value = mock_manager
        yield mock_manager


@pytest.fixture
def mock_agent_creator():
    """Mock agent creator."""
    with patch("agentic_fleet.chainlit_app.create_magentic_one_agent") as mock_creator:
        mock_agent = MagicMock()
        mock_creator.return_value = mock_agent
        yield mock_creator


@pytest.fixture
def mock_message_handler():
    """Mock message handler."""
    with patch("agentic_fleet.chainlit_app.handle_chat_message") as mock_handler:
        mock_handler.return_value = AsyncMock()
        yield mock_handler


@pytest.fixture
def mock_settings_manager():
    """Mock settings manager."""
    with patch("agentic_fleet.chainlit_app.SettingsManager") as mock_settings_cls:
        mock_settings = MagicMock()
        mock_settings.get_default_settings = MagicMock(return_value={"temperature": 0.7})
        mock_settings.setup_chat_settings = AsyncMock()
        mock_settings.handle_settings_update = AsyncMock()
        mock_settings_cls.return_value = mock_settings
        yield mock_settings


@pytest.fixture
def mock_task_manager():
    """Mock task manager."""
    with patch("agentic_fleet.chainlit_app.initialize_task_list") as mock_init_task:
        mock_init_task.return_value = AsyncMock()
        yield mock_init_task


@pytest.mark.asyncio
async def test_start_chat_default_profile(
    mock_chainlit, mock_config_manager, mock_client, 
    mock_app_manager, mock_agent_creator, mock_task_manager, mock_settings_manager
):
    """Test start_chat function with default profile."""
    # Setup
    mock_chainlit.user_session.get.return_value = "default"

    # Execute
    await chainlit_app.start_chat()

    # Assert
    mock_config_manager.load_all.assert_called_once()
    mock_config_manager.validate_environment.assert_called_once()

    # Check if agent was created with correct params
    mock_agent_creator.assert_called_once_with(
        client=mock_client,
        hil_mode=True
    )

    # Check if user session values were set
    assert mock_chainlit.user_session.set.call_args_list

    # Check if welcome message was sent
    mock_chainlit.Message.assert_called()
    mock_chainlit.Message().send.assert_awaited()


@pytest.mark.asyncio
async def test_start_chat_mcp_focus_profile(
    mock_chainlit, mock_config_manager, mock_client, 
    mock_app_manager, mock_agent_creator, mock_task_manager, mock_settings_manager
):
    """Test start_chat function with MCP Focus profile."""
    # Setup
    mock_chainlit.user_session.get.return_value = "MCP Focus"

    # Execute
    await chainlit_app.start_chat()

    # Assert
    # Check if agent was created with correct params
    mock_agent_creator.assert_called_once_with(
        client=mock_client,
        hil_mode=True
        # mcp_enabled parameter removed as it's not supported by MagenticOne
    )

    # Check if user session was set with custom render mode
    assert mock_chainlit.user_session.set.call_args_list


@pytest.mark.asyncio
async def test_start_chat_error_handling(
    mock_chainlit, mock_config_manager, mock_client, mock_app_manager
):
    """Test error handling in start_chat function."""
    # Setup
    mock_config_manager.validate_environment.return_value = "Missing API key"

    # Execute
    await chainlit_app.start_chat()

    # Assert
    mock_chainlit.Message.assert_called_with(content="⚠️ Initialization failed: Missing API key")
    mock_chainlit.Message().send.assert_awaited()


@pytest.mark.asyncio
async def test_message_handler(mock_chainlit, mock_message_handler):
    """Test message handler function."""
    # Setup
    mock_message = MagicMock()

    # Execute
    await chainlit_app.message_handler(mock_message)

    # Assert
    mock_message_handler.assert_called_once_with(mock_message)
    mock_message_handler.assert_awaited_with(mock_message)


@pytest.mark.asyncio
async def test_handle_settings_update(mock_chainlit, mock_settings_manager):
    """Test handle_settings_update function."""
    # Setup
    mock_settings = {"temperature": 0.8}

    # Execute
    await chainlit_app.handle_settings_update(mock_settings)

    # Assert
    # Check if settings manager's handle_settings_update was called
    assert mock_settings_manager.handle_settings_update.call_args == call(mock_settings)


@pytest.mark.asyncio
async def test_on_action_reset():
    """Test on_action_reset function."""
    # Setup
    mock_action = MagicMock()

    with patch("agentic_fleet.chainlit_app.on_reset", new_callable=AsyncMock) as mock_reset:
        # Execute
        await chainlit_app.on_action_reset(mock_action)

        # Assert
        mock_reset.assert_called_once_with(mock_action)
        mock_reset.assert_awaited_with(mock_action)


@pytest.mark.asyncio
async def test_on_action_list_mcp_no_servers(mock_chainlit):
    """Test on_action_list_mcp function with no servers."""
    # Setup
    mock_action = MagicMock()
    mock_chainlit.user_session.get.return_value = []

    # Execute
    await chainlit_app.on_action_list_mcp(mock_action)

    # Assert
    mock_chainlit.Message.assert_called_with(
        content="No MCP servers currently connected. Use `connect_mcp_server` to connect.",
        author="MCP Manager"
    )
    mock_chainlit.Message().send.assert_awaited()


@pytest.mark.asyncio
async def test_on_action_list_mcp_with_servers(mock_chainlit):
    """Test on_action_list_mcp function with servers."""
    # Setup
    mock_action = MagicMock()

    # Create mock servers with tools
    mock_tool = MagicMock()
    mock_tool.name = "TestTool"
    mock_tool.description = "A test tool"

    mock_server = MagicMock()
    mock_server.name = "TestServer"
    mock_server.tools = [mock_tool]

    mock_chainlit.user_session.get.return_value = [mock_server]

    # Execute
    await chainlit_app.on_action_list_mcp(mock_action)

    # Assert
    mock_chainlit.Message.assert_called()
    # Check that message contains tool info
    call_args = mock_chainlit.Message.call_args
    assert "TestServer" in call_args[1]["content"]
    assert "TestTool" in call_args[1]["content"]
    mock_chainlit.Message().send.assert_awaited()


@pytest.mark.asyncio
async def test_on_chat_stop(mock_chainlit):
    """Test on_chat_stop function."""
    # Setup
    chainlit_app.app_manager = MagicMock()
    chainlit_app.app_manager.shutdown = AsyncMock()

    # Execute
    await chainlit_app.on_chat_stop()

    # Assert
    chainlit_app.app_manager.shutdown.assert_awaited()
    assert mock_chainlit.user_session.set.call_args_list


def test_main():
    """Test main function."""
    with patch("agentic_fleet.chainlit_app.subprocess.run") as mock_run, \
         patch("agentic_fleet.chainlit_app.sys.exit") as mock_exit, \
         patch("agentic_fleet.chainlit_app.os.path.abspath") as mock_abspath:

        # Setup
        mock_abspath.return_value = "/path/to/chainlit_app.py"
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Execute
        chainlit_app.main()

        # Assert
        mock_run.assert_called_once()
        assert "chainlit" in mock_run.call_args[0][0][0]
        mock_exit.assert_called_once_with(0)


def test_main_error_handling():
    """Test error handling in the main function."""
    with patch("agentic_fleet.chainlit_app.subprocess.run") as mock_run, \
         patch("agentic_fleet.chainlit_app.sys.exit") as mock_exit:

        # Setup
        mock_run.side_effect = FileNotFoundError("No such file")

        # Execute
        chainlit_app.main()

        # Assert
        mock_exit.assert_called_once_with(1)
