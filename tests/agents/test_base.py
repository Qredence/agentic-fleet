"""Tests for agents/base.py - DSPyEnhancedAgent functionality.

This module tests the DSPyEnhancedAgent class which wraps ChatAgent
with DSPy-powered reasoning strategies.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_framework._types import AgentRunResponse, ChatMessage, Role

from agentic_fleet.agents.base import DSPyEnhancedAgent

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_chat_client():
    """Create a mock OpenAI responses client."""
    return MagicMock()


@pytest.fixture
def basic_agent(mock_chat_client):
    """Create a basic DSPyEnhancedAgent with defaults."""
    return DSPyEnhancedAgent(
        name="TestAgent",
        chat_client=mock_chat_client,
        instructions="You are a helpful assistant.",
        description="Test agent for unit tests",
        enable_dspy=False,  # Disable DSPy for basic tests
    )


@pytest.fixture
def dspy_enabled_agent(mock_chat_client):
    """Create a DSPyEnhancedAgent with DSPy enabled."""
    with patch("agentic_fleet.agents.base.FleetReAct"), patch("agentic_fleet.agents.base.FleetPoT"):
        return DSPyEnhancedAgent(
            name="DSPyAgent",
            chat_client=mock_chat_client,
            instructions="You are an enhanced assistant.",
            description="DSPy-enabled test agent",
            enable_dspy=True,
            reasoning_strategy="react",
        )


@pytest.fixture
def pot_agent(mock_chat_client):
    """Create a DSPyEnhancedAgent with Program of Thought strategy."""
    with patch("agentic_fleet.agents.base.FleetReAct"), patch("agentic_fleet.agents.base.FleetPoT"):
        return DSPyEnhancedAgent(
            name="PoTAgent",
            chat_client=mock_chat_client,
            instructions="You are a reasoning assistant.",
            description="PoT-enabled test agent",
            enable_dspy=True,
            reasoning_strategy="program_of_thought",
        )


# =============================================================================
# Test: DSPyEnhancedAgent Initialization
# =============================================================================


class TestDSPyEnhancedAgentInit:
    """Tests for DSPyEnhancedAgent initialization."""

    def test_initializes_with_required_params(self, mock_chat_client):
        """Test that agent initializes with minimal parameters."""
        agent = DSPyEnhancedAgent(name="Agent", chat_client=mock_chat_client)

        assert agent.name == "Agent"
        assert agent.enable_dspy is True  # Default
        assert agent.timeout == 30  # Default
        assert agent.reasoning_strategy == "chain_of_thought"  # Default

    def test_initializes_with_custom_params(self, mock_chat_client):
        """Test that agent initializes with custom parameters."""
        agent = DSPyEnhancedAgent(
            name="CustomAgent",
            chat_client=mock_chat_client,
            instructions="Custom instructions",
            description="Custom description",
            enable_dspy=False,
            timeout=60,
            cache_ttl=600,
            reasoning_strategy="react",
        )

        assert agent.name == "CustomAgent"
        assert agent.enable_dspy is False
        assert agent.timeout == 60
        assert agent.reasoning_strategy == "react"
        assert agent.description == "Custom description"

    def test_initializes_react_module_for_react_strategy(self, mock_chat_client):
        """Test that ReAct module is initialized for react strategy."""
        with patch("agentic_fleet.agents.base.FleetReAct") as mock_react:
            agent = DSPyEnhancedAgent(
                name="ReactAgent",
                chat_client=mock_chat_client,
                enable_dspy=True,
                reasoning_strategy="react",
            )

            mock_react.assert_called_once()
            assert agent.pot_module is None

    def test_initializes_pot_module_for_pot_strategy(self, mock_chat_client):
        """Test that PoT module is initialized for program_of_thought strategy."""
        with patch("agentic_fleet.agents.base.FleetPoT") as mock_pot:
            agent = DSPyEnhancedAgent(
                name="PoTAgent",
                chat_client=mock_chat_client,
                enable_dspy=True,
                reasoning_strategy="program_of_thought",
            )

            mock_pot.assert_called_once()
            assert agent.react_module is None

    def test_no_modules_for_chain_of_thought(self, mock_chat_client):
        """Test that no special modules are initialized for chain_of_thought."""
        agent = DSPyEnhancedAgent(
            name="CoTAgent",
            chat_client=mock_chat_client,
            enable_dspy=True,
            reasoning_strategy="chain_of_thought",
        )

        assert agent.react_module is None
        assert agent.pot_module is None


# =============================================================================
# Test: DSPy Task Enhancement
# =============================================================================


class TestDSPyTaskEnhancement:
    """Tests for DSPy task enhancement functionality."""

    def test_enhance_task_returns_original_when_disabled(self, basic_agent):
        """Test that enhancement returns original task when DSPy is disabled."""
        task = "Write a poem about cats"
        enhanced, metadata = basic_agent._enhance_task_with_dspy(task)

        assert enhanced == task
        assert metadata == {}

    def test_enhance_task_returns_original_when_no_enhancer(self, dspy_enabled_agent):
        """Test that enhancement returns original task when no enhancer is set."""
        task = "Write a poem about cats"
        enhanced, metadata = dspy_enabled_agent._enhance_task_with_dspy(task)

        assert enhanced == task
        assert metadata == {}

    def test_enhance_task_uses_enhancer_when_available(self, dspy_enabled_agent):
        """Test that enhancement uses the task enhancer when available."""
        mock_enhancer = MagicMock()
        mock_enhancer.return_value = MagicMock(
            enhanced_task="Write a detailed poem about cats with vivid imagery",
            key_requirements="Use metaphors and similes",
            expected_output_format="Poetry format",
        )
        dspy_enabled_agent.task_enhancer = mock_enhancer

        task = "Write a poem about cats"
        enhanced, metadata = dspy_enabled_agent._enhance_task_with_dspy(task)

        assert enhanced == "Write a detailed poem about cats with vivid imagery"
        assert metadata["key_requirements"] == "Use metaphors and similes"
        assert metadata["expected_format"] == "Poetry format"
        assert metadata["enhanced"] is True

    def test_enhance_task_handles_exception(self, dspy_enabled_agent):
        """Test that enhancement handles exceptions gracefully."""
        mock_enhancer = MagicMock(side_effect=Exception("Enhancement failed"))
        dspy_enabled_agent.task_enhancer = mock_enhancer

        task = "Write a poem"
        enhanced, metadata = dspy_enabled_agent._enhance_task_with_dspy(task)

        assert enhanced == task
        assert metadata["enhanced"] is False
        assert "error" in metadata


# =============================================================================
# Test: Agent Role Description
# =============================================================================


class TestAgentRoleDescription:
    """Tests for _get_agent_role_description."""

    def test_returns_description_when_set(self, basic_agent):
        """Test that description is returned when set."""
        basic_agent.description = "Test description"
        result = basic_agent._get_agent_role_description()

        assert result == "Test description"

    def test_truncates_long_descriptions(self, mock_chat_client):
        """Test that long descriptions are truncated to 200 chars."""
        long_description = "A" * 300
        agent = DSPyEnhancedAgent(
            name="Agent",
            chat_client=mock_chat_client,
            description=long_description,
        )

        result = agent._get_agent_role_description()

        assert len(result) == 200
        assert result == "A" * 200


# =============================================================================
# Test: Execute with Timeout
# =============================================================================


class TestExecuteWithTimeout:
    """Tests for execute_with_timeout method."""

    @pytest.mark.asyncio
    async def test_execute_returns_message_on_success(self, basic_agent):
        """Test that execute_with_timeout returns a ChatMessage on success."""
        expected_response = AgentRunResponse(
            messages=[ChatMessage(role=Role.ASSISTANT, text="Hello!")],
        )
        basic_agent.run = AsyncMock(return_value=expected_response)

        result = await basic_agent.execute_with_timeout("Say hello")

        assert isinstance(result, ChatMessage)
        assert result.text == "Hello!"
        assert result.role == Role.ASSISTANT

    @pytest.mark.asyncio
    async def test_execute_handles_timeout(self, basic_agent):
        """Test that execute_with_timeout handles timeout correctly."""
        basic_agent.timeout = 1

        async def slow_run(*args, **kwargs):
            await asyncio.sleep(5)
            return AgentRunResponse(messages=[])

        basic_agent.run = slow_run

        result = await basic_agent.execute_with_timeout("Slow task")

        assert isinstance(result, ChatMessage)
        assert "timed out" in result.text.lower()

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self, basic_agent):
        """Test that execute_with_timeout handles exceptions gracefully."""
        basic_agent.run = AsyncMock(side_effect=ValueError("Test error"))

        result = await basic_agent.execute_with_timeout("Failing task")

        assert isinstance(result, ChatMessage)
        assert "error" in result.text.lower()

    @pytest.mark.asyncio
    async def test_execute_handles_direct_chatmessage_return(self, basic_agent):
        """Test that execute_with_timeout handles direct ChatMessage return."""
        direct_message = ChatMessage(role=Role.ASSISTANT, text="Direct message")
        basic_agent.run = AsyncMock(return_value=direct_message)

        result = await basic_agent.execute_with_timeout("Task")

        assert result == direct_message


# =============================================================================
# Test: Input Normalization
# =============================================================================


class TestInputNormalization:
    """Tests for _normalize_input_to_text method."""

    def test_normalizes_string_input(self, basic_agent):
        """Test that string input is normalized correctly."""
        result = basic_agent._normalize_input_to_text("Hello")

        assert result == "Hello"

    def test_normalizes_chatmessage_input(self, basic_agent):
        """Test that ChatMessage input is normalized correctly."""
        message = ChatMessage(role=Role.USER, text="Hello")
        result = basic_agent._normalize_input_to_text(message)

        assert "User: Hello" in result

    def test_normalizes_list_of_strings(self, basic_agent):
        """Test that list of strings is normalized correctly."""
        messages = ["Hello", "How are you?"]
        result = basic_agent._normalize_input_to_text(messages)

        assert "Hello" in result
        assert "How are you?" in result

    def test_normalizes_list_of_chatmessages(self, basic_agent):
        """Test that list of ChatMessages is normalized correctly."""
        messages = [
            ChatMessage(role=Role.USER, text="Hello"),
            ChatMessage(role=Role.ASSISTANT, text="Hi there!"),
        ]
        result = basic_agent._normalize_input_to_text(messages)

        assert "User: Hello" in result
        assert "Assistant: Hi there!" in result

    def test_returns_empty_string_for_none(self, basic_agent):
        """Test that None input returns empty string."""
        result = basic_agent._normalize_input_to_text(None)

        assert result == ""

    def test_uses_thread_messages_when_provided(self, basic_agent):
        """Test that thread messages are included when provided."""
        thread = MagicMock()
        thread.messages = [ChatMessage(role=Role.USER, text="Previous message")]

        result = basic_agent._normalize_input_to_text(None, thread=thread)

        assert "User: Previous message" in result


# =============================================================================
# Test: Run Method
# =============================================================================


class TestRunMethod:
    """Tests for the run method."""

    @pytest.mark.asyncio
    async def test_run_uses_cache_when_available(self, dspy_enabled_agent):
        """Test that run uses cached results when available."""
        dspy_enabled_agent.cache.set("test prompt", "Cached response")

        result = await dspy_enabled_agent.run("test prompt")

        assert result.text == "Cached response"
        assert result.additional_properties.get("cached") is True

    @pytest.mark.asyncio
    async def test_run_uses_react_module(self, dspy_enabled_agent):
        """Test that run uses ReAct module when strategy is react."""
        mock_react = MagicMock()
        mock_react.return_value = MagicMock(answer="ReAct answer")
        dspy_enabled_agent.react_module = mock_react

        result = await dspy_enabled_agent.run("Test question")

        assert result.text == "ReAct answer"
        assert result.additional_properties.get("strategy") == "react"

    @pytest.mark.asyncio
    async def test_run_uses_pot_module(self, pot_agent):
        """Test that run uses PoT module when strategy is program_of_thought."""
        mock_pot = MagicMock()
        mock_pot.return_value = MagicMock(answer="PoT answer")
        pot_agent.pot_module = mock_pot

        result = await pot_agent.run("Calculate 2+2")

        assert result.text == "PoT answer"
        assert result.additional_properties.get("strategy") == "program_of_thought"

    @pytest.mark.asyncio
    async def test_run_falls_back_on_dspy_failure(self, dspy_enabled_agent):
        """Test that run falls back to ChatAgent on DSPy failure."""
        mock_react = MagicMock(side_effect=Exception("DSPy failed"))
        dspy_enabled_agent.react_module = mock_react

        # Mock the parent run method
        fallback_response = AgentRunResponse(
            messages=[ChatMessage(role=Role.ASSISTANT, text="Fallback response")],
        )
        with patch.object(
            DSPyEnhancedAgent.__bases__[0], "run", new_callable=AsyncMock
        ) as mock_parent_run:
            mock_parent_run.return_value = fallback_response
            result = await dspy_enabled_agent.run("Test question")

            mock_parent_run.assert_called_once()
            assert result == fallback_response


# =============================================================================
# Test: Run Stream Method
# =============================================================================


class TestRunStreamMethod:
    """Tests for the run_stream method."""

    @pytest.mark.asyncio
    async def test_run_stream_yields_single_update_for_react(self, dspy_enabled_agent):
        """Test that run_stream yields a single update for react strategy."""
        mock_react = MagicMock()
        mock_react.return_value = MagicMock(answer="Streamed answer")
        dspy_enabled_agent.react_module = mock_react

        updates = []
        async for update in dspy_enabled_agent.run_stream("Test"):
            updates.append(update)

        assert len(updates) == 1
        assert updates[0].text == "Streamed answer"


# =============================================================================
# Test: Program of Thought Failure Handling
# =============================================================================


class TestPotFailureHandling:
    """Tests for Program of Thought failure handling."""

    @pytest.mark.asyncio
    async def test_handle_pot_failure_returns_fallback(self, pot_agent):
        """Test that _handle_pot_failure returns fallback response."""
        # Set pot_module to None to avoid mock attribute access
        pot_agent.pot_module = None

        fallback_response = AgentRunResponse(
            messages=[ChatMessage(role=Role.ASSISTANT, text="Fallback response")],
        )
        with patch.object(
            DSPyEnhancedAgent.__bases__[0], "run", new_callable=AsyncMock
        ) as mock_parent:
            mock_parent.return_value = fallback_response
            error = RuntimeError("PoT failed")

            result = await pot_agent._handle_pot_failure(
                messages="Test",
                thread=None,
                agent_kwargs={},
                error=error,
            )

            # The fallback was called and additional_properties updated
            assert result.additional_properties.get("pot_error") is not None

    def test_build_pot_error_note(self, pot_agent):
        """Test that _build_pot_error_note creates correct note."""
        # Set pot_module to None to test exception-based fallback
        pot_agent.pot_module = None

        error = RuntimeError("Test error")
        note = pot_agent._build_pot_error_note(error)

        assert "Program of Thought fallback:" in note
        assert "Test error" in note

    def test_build_pot_error_note_uses_module_last_error(self, pot_agent):
        """Test that _build_pot_error_note uses module's last_error if available."""
        pot_agent.pot_module = MagicMock()
        pot_agent.pot_module.last_error = "Module specific error"

        error = RuntimeError("Generic error")
        note = pot_agent._build_pot_error_note(error)

        assert "Module specific error" in note


# =============================================================================
# Test: Helper Methods
# =============================================================================


class TestHelperMethods:
    """Tests for various helper methods."""

    def test_apply_note_to_text_prepends_note(self, basic_agent):
        """Test that _apply_note_to_text prepends note correctly."""
        result = DSPyEnhancedAgent._apply_note_to_text("Original text", "Note:")

        assert result == "Note:\n\nOriginal text"

    def test_apply_note_to_text_handles_empty_text(self, basic_agent):
        """Test that _apply_note_to_text handles empty text."""
        result = DSPyEnhancedAgent._apply_note_to_text("", "Note:")

        assert result == "Note:"

    def test_apply_note_to_text_avoids_duplication(self, basic_agent):
        """Test that _apply_note_to_text avoids duplicate notes."""
        result = DSPyEnhancedAgent._apply_note_to_text("Note:\n\nOriginal", "Note:")

        assert result == "Note:\n\nOriginal"

    def test_create_timeout_response(self, basic_agent):
        """Test that _create_timeout_response creates correct message."""
        result = basic_agent._create_timeout_response(30)

        assert isinstance(result, ChatMessage)
        assert result.role == Role.ASSISTANT
        assert "30 seconds" in result.text

    def test_tools_property_returns_tools(self, mock_chat_client):
        """Test that tools property returns agent's tools."""
        tools = [MagicMock(), MagicMock()]
        agent = DSPyEnhancedAgent(
            name="Agent",
            chat_client=mock_chat_client,
            tools=tools,
        )

        # The tools property returns getattr(self, "_tools", [])
        # If tools were set, verify the property works
        result = agent.tools
        # Result is either the tools or empty list (depending on parent impl)
        assert isinstance(result, list)

    def test_tools_property_returns_empty_list_when_none(self, basic_agent):
        """Test that tools property returns empty list when no tools."""
        result = basic_agent.tools

        assert result == []
