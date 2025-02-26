"""Tests for the app module."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# Import the functions we want to test
from agentic_fleet.app import start_chat, message_handler, handle_settings_update


@pytest.mark.asyncio
async def test_start_chat(mock_user_session, mock_chainlit_elements, mock_env_vars):
    """Test that start_chat initializes properly."""
    # Mock cl.ChatProfile
    mock_profile = MagicMock()
    mock_profile.name = "Test Profile"
    mock_profile.markdown_description = "Test description"
    mock_profile.model_settings = {"model_name": "gpt-4o-mini-2024-07-18"}
    
    # Mock the application manager
    with patch("agentic_fleet.app.ApplicationManager") as mock_app_manager_class:
        mock_app_manager = mock_app_manager_class.return_value
        mock_app_manager.start = AsyncMock()
        
        # Mock the MagenticOne team
        with patch("agentic_fleet.app.MagenticOne") as mock_team_class:
            mock_team = mock_team_class.return_value
            
            # Call the function
            await start_chat(mock_profile)
            
            # Verify the application manager was started
            mock_app_manager.start.assert_called_once()
            
            # Verify the team was created and stored in the session
            mock_team_class.assert_called_once()
            assert mock_user_session.get.call_args_list[0][0][0] == "agent_team"
            
            # Verify that a welcome message was sent
            message_instance = mock_chainlit_elements["Message"].return_value
            assert message_instance.send.called


@pytest.mark.asyncio
async def test_message_handler(mock_user_session, mock_chainlit_elements):
    """Test that message_handler calls handle_chat_message."""
    # Create a mock message
    mock_message = MagicMock()
    
    # Patch the handle_chat_message function
    with patch("agentic_fleet.app.handle_chat_message") as mock_handle_message:
        mock_handle_message.return_value = AsyncMock()
        
        # Call the function
        await message_handler(mock_message)
        
        # Verify handle_chat_message was called with the message
        mock_handle_message.assert_called_once_with(mock_message)


@pytest.mark.asyncio
async def test_handle_settings_update(mock_user_session, mock_settings_components):
    """Test that handle_settings_update calls the settings manager."""
    # Create mock settings
    mock_settings = MagicMock()
    
    # Patch the settings_manager
    with patch("agentic_fleet.app.settings_manager") as mock_settings_manager:
        mock_settings_manager.handle_settings_update = AsyncMock()
        
        # Call the function
        await handle_settings_update(mock_settings)
        
        # Verify settings_manager.handle_settings_update was called
        mock_settings_manager.handle_settings_update.assert_called_once_with(mock_settings)


@pytest.mark.asyncio
async def test_on_action_reset(mock_chainlit_elements):
    """Test that the reset action callback calls on_reset."""
    # Create a mock action
    mock_action = MagicMock()
    
    # Patch the on_reset function
    with patch("agentic_fleet.app.on_reset") as mock_on_reset:
        mock_on_reset.return_value = AsyncMock()
        
        # Import the function to test to force its resolution
        from agentic_fleet.app import on_action_reset
        
        # Call the function
        await on_action_reset(mock_action)
        
        # Verify on_reset was called with the action
        mock_on_reset.assert_called_once_with(mock_action)


@pytest.mark.asyncio
async def test_on_chat_stop(mock_user_session):
    """Test that on_chat_stop cleans up resources properly."""
    # Create a mock application manager
    mock_app_manager = MagicMock()
    mock_app_manager.stop = AsyncMock()
    
    # Patch the global app_manager
    with patch("agentic_fleet.app.app_manager", mock_app_manager):
        # Import the function to test to force its resolution
        from agentic_fleet.app import on_chat_stop
        
        # Call the function
        await on_chat_stop()
        
        # Verify app_manager.stop was called
        mock_app_manager.stop.assert_called_once()
        
        # Verify user session was cleared
        mock_user_session.clear.assert_called_once()
