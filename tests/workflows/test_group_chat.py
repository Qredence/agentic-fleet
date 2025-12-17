"""Tests for DSPy-powered Group Chat."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from agent_framework._types import ChatMessage, Role

from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
from agentic_fleet.workflows.strategies.group_chat_adapter import (
    DSPyGroupChatManager,
    GroupChatBuilder,
)


@pytest.fixture
def mock_agent_with_run():
    """Create a mock agent that has the `run` method."""
    agent = MagicMock()
    agent.name = "MockAgent"
    agent.description = "A mock agent with run method"

    response = ChatMessage(
        role=Role.ASSISTANT,
        text="Hello from run",
        additional_properties={"name": "MockAgent"},
    )

    # Mock run to return an object with messages attribute
    run_response = MagicMock()
    run_response.messages = [response]
    run_response.text = "Hello from run"
    run_response.additional_properties = {}
    agent.run = AsyncMock(return_value=run_response)

    # Remove process to ensure run path is tested
    agent.process = None

    return agent


@pytest.fixture
def mock_agent_with_process_only():
    """Create a mock agent that only has the `process` method (legacy support)."""
    agent = MagicMock()
    agent.name = "LegacyAgent"
    agent.description = "A mock agent with only process method"

    response = ChatMessage(
        role=Role.ASSISTANT,
        text="Hello from process",
        additional_properties={"name": "LegacyAgent"},
    )

    agent.process = AsyncMock(return_value=response)

    # Remove run to ensure process path is tested
    agent.run = None

    return agent


@pytest.fixture
def mock_agent_with_neither():
    """Create a mock agent that has neither run nor process methods."""
    # Use spec to limit attributes, then configure only what we need
    agent = MagicMock(spec=["name", "description"])
    agent.name = "FallbackAgent"
    agent.description = "A mock agent with neither run nor process"

    # With spec=[], the mock won't have run or process attributes at all
    # hasattr(agent, "run") will now return False

    return agent


@pytest.fixture
def mock_reasoner():
    reasoner = MagicMock(spec=DSPyReasoner)
    reasoner.select_next_speaker.return_value = {
        "next_speaker": "MockAgent",
        "reasoning": "Test",
    }
    return reasoner


def test_group_chat_builder(mock_agent_with_run, mock_reasoner):
    """Test that GroupChatBuilder creates a valid DSPyGroupChatManager."""
    builder = GroupChatBuilder()
    builder.add_agent(mock_agent_with_run)
    builder.set_reasoner(mock_reasoner)
    builder.set_max_rounds(5)

    manager = builder.build()

    assert isinstance(manager, DSPyGroupChatManager)
    assert manager.max_rounds == 5
    assert "MockAgent" in manager.agents


@pytest.mark.asyncio
async def test_group_chat_run_with_run_method(mock_agent_with_run, mock_reasoner):
    """Test group chat with agent that has `run` method."""
    # Setup reasoner to select agent once then terminate
    mock_reasoner.select_next_speaker.side_effect = [
        {"next_speaker": "MockAgent", "reasoning": "First turn"},
        {"next_speaker": "TERMINATE", "reasoning": "Done"},
    ]

    manager = DSPyGroupChatManager(
        agents=[mock_agent_with_run], reasoner=mock_reasoner, max_rounds=5
    )

    history = await manager.run_chat("Start chat")

    assert len(history) == 2  # User message + 1 agent response
    assert history[0].role == Role.USER
    assert history[0].text == "Start chat"
    assert history[1].role == Role.ASSISTANT
    assert history[1].text == "Hello from run"
    assert history[1].additional_properties["name"] == "MockAgent"

    # Verify run was called (not process)
    assert mock_agent_with_run.run.called
    assert mock_agent_with_run.process is None


@pytest.mark.asyncio
async def test_group_chat_run_with_process_method(mock_agent_with_process_only, mock_reasoner):
    """Test group chat with agent that only has `process` method (legacy support)."""
    # Setup reasoner to select agent once then terminate
    mock_reasoner.select_next_speaker.side_effect = [
        {"next_speaker": "LegacyAgent", "reasoning": "First turn"},
        {"next_speaker": "TERMINATE", "reasoning": "Done"},
    ]

    manager = DSPyGroupChatManager(
        agents=[mock_agent_with_process_only], reasoner=mock_reasoner, max_rounds=5
    )

    history = await manager.run_chat("Start chat")

    assert len(history) == 2  # User message + 1 agent response
    assert history[0].role == Role.USER
    assert history[0].text == "Start chat"
    assert history[1].role == Role.ASSISTANT
    assert history[1].text == "Hello from process"
    assert history[1].additional_properties["name"] == "LegacyAgent"

    # Verify process was called (not run)
    assert mock_agent_with_process_only.process.called
    assert mock_agent_with_process_only.run is None


@pytest.mark.asyncio
async def test_group_chat_run_with_fallback(mock_agent_with_neither, mock_reasoner):
    """Test group chat with agent that has neither run nor process (fallback case)."""
    # Setup reasoner to select agent once then terminate
    mock_reasoner.select_next_speaker.side_effect = [
        {"next_speaker": "FallbackAgent", "reasoning": "First turn"},
        {"next_speaker": "TERMINATE", "reasoning": "Done"},
    ]

    manager = DSPyGroupChatManager(
        agents=[mock_agent_with_neither], reasoner=mock_reasoner, max_rounds=5
    )

    history = await manager.run_chat("Start chat")

    assert len(history) == 2  # User message + 1 fallback response
    assert history[0].role == Role.USER
    assert history[0].text == "Start chat"
    assert history[1].role == Role.ASSISTANT
    # Fallback response should still have the agent name
    assert history[1].additional_properties["name"] == "FallbackAgent"
    # Verify fallback response text/content (should be non-empty)
    assert "FallbackAgent" in history[1].text

    # Verify neither run nor process exist on the mock (spec limits attributes)
    assert not hasattr(mock_agent_with_neither, "run")
    assert not hasattr(mock_agent_with_neither, "process")
