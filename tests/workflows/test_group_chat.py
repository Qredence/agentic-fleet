"""Tests for DSPy-powered Group Chat."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from agent_framework._types import ChatMessage, Role

from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
from agentic_fleet.workflows.group_chat_adapter import DSPyGroupChatManager
from agentic_fleet.workflows.group_chat_builder import GroupChatBuilder


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.name = "MockAgent"
    agent.description = "A mock agent"

    response = ChatMessage(
        role=Role.ASSISTANT,
        text="Hello",
        additional_properties={"name": "MockAgent"},
    )

    # Configure both run and process for compatibility testing
    agent.process = AsyncMock(return_value=response)

    # Mock run to return an object with messages attribute
    run_response = MagicMock()
    run_response.messages = [response]
    run_response.text = "Hello"
    run_response.additional_properties = {}
    agent.run = AsyncMock(return_value=run_response)

    return agent


@pytest.fixture
def mock_reasoner():
    reasoner = MagicMock(spec=DSPyReasoner)
    reasoner.select_next_speaker.return_value = {
        "next_speaker": "MockAgent",
        "reasoning": "Test",
    }
    return reasoner


@pytest.mark.asyncio
def test_group_chat_builder(mock_agent, mock_reasoner):
    builder = GroupChatBuilder()
    builder.add_agent(mock_agent)
    builder.set_reasoner(mock_reasoner)
    builder.set_max_rounds(5)

    manager = builder.build()

    assert isinstance(manager, DSPyGroupChatManager)
    assert manager.max_rounds == 5
    assert "MockAgent" in manager.agents


@pytest.mark.asyncio
async def test_group_chat_run(mock_agent, mock_reasoner):
    # Setup reasoner to select agent once then terminate
    mock_reasoner.select_next_speaker.side_effect = [
        {"next_speaker": "MockAgent", "reasoning": "First turn"},
        {"next_speaker": "TERMINATE", "reasoning": "Done"},
    ]

    manager = DSPyGroupChatManager(agents=[mock_agent], reasoner=mock_reasoner, max_rounds=5)

    history = await manager.run_chat("Start chat")

    assert len(history) == 2  # User message + 1 agent response
    assert history[0].role == Role.USER
    assert history[0].text == "Start chat"
    assert history[1].role == Role.ASSISTANT
    assert history[1].text == "Hello"
    assert history[1].additional_properties["name"] == "MockAgent"

    assert mock_agent.run.called or mock_agent.process.called
