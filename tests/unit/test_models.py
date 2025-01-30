"""Unit tests for the models module."""
import pytest
from unittest.mock import Mock, patch
from autogen.core.provider import ChatCompletionClient

from agentic_fleet.models.models import (
    EnhancedAssistantAgent,
    EnhancedUserProxyAgent,
    create_azure_client,
    create_agent_team
)

@pytest.fixture
def mock_model_client():
    return Mock(spec=ChatCompletionClient)

@pytest.mark.asyncio
async def test_enhanced_assistant_agent_initialization():
    """Test EnhancedAssistantAgent initialization."""
    agent = EnhancedAssistantAgent(
        name="test_agent",
        system_message="test message"
    )
    assert agent.name == "test_agent"
    assert isinstance(agent, EnhancedAssistantAgent)

@pytest.mark.asyncio
async def test_enhanced_assistant_agent_process_message(mock_model_client):
    """Test message processing in EnhancedAssistantAgent."""
    agent = EnhancedAssistantAgent(
        name="test_agent",
        system_message="test message",
        model_client=mock_model_client
    )
    
    mock_model_client.generate.return_value = "test response"
    
    result = await agent.process_message("test message")
    assert result is not None

@pytest.mark.asyncio
async def test_enhanced_assistant_agent_error_handling(mock_model_client):
    """Test error handling in EnhancedAssistantAgent."""
    agent = EnhancedAssistantAgent(
        name="test_agent",
        system_message="test message",
        model_client=mock_model_client
    )
    
    mock_model_client.generate.side_effect = Exception("test error")
    
    with pytest.raises(Exception):
        await agent.process_message("test message")

@pytest.mark.asyncio
async def test_create_agent_team():
    """Test agent team creation."""
    team = await create_agent_team("test task")
    assert team is not None
    assert isinstance(team, MagenticOneGroupChat)
