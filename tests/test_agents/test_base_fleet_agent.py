"""Unit tests for BaseFleetAgent."""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import dspy
from agent_framework import ChatMessage, Role

from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.dspy_modules.signatures import PlannerSignature, TaskContext


class TestBaseFleetAgentMessageCoercion:
    """Tests for _coerce_messages method."""

    def test_string_input(self):
        """Test that string input is returned as-is."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        result = agent._coerce_messages("hello world")
        assert result == "hello world"

    def test_chat_message_input(self):
        """Test that ChatMessage text is extracted."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        msg = ChatMessage(role=Role.USER, text="test message")
        result = agent._coerce_messages(msg)
        assert result == "test message"

    def test_chat_message_with_none_text(self):
        """Test ChatMessage with None text falls back to str()."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        msg = MagicMock()
        msg.text = None
        msg.__str__ = lambda s: "mock str"
        msg.__iter__ = lambda s: iter([])

        result = agent._coerce_messages(msg)
        assert result == "mock str"

    def test_list_of_strings(self):
        """Test list of strings is joined with newlines."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        result = agent._coerce_messages(["hello", "world"])
        assert result == "hello\nworld"

    def test_list_of_chat_messages(self):
        """Test list of ChatMessages extracts text."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        messages = [
            ChatMessage(role=Role.USER, text="first"),
            ChatMessage(role=Role.ASSISTANT, text="second"),
        ]
        result = agent._coerce_messages(messages)
        assert result == "first\nsecond"

    def test_list_mixed_strings_and_chat_messages(self):
        """Test list with mixed strings and ChatMessages."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        messages = [
            "string message",
            ChatMessage(role=Role.USER, text="chat message"),
        ]
        result = agent._coerce_messages(messages)
        assert result == "string message\nchat message"

    def test_none_input(self):
        """Test that None returns empty string."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        result = agent._coerce_messages(None)
        assert result == ""


class TestBaseFleetAgentTeamResolution:
    """Tests for _resolve_team_id method."""

    def test_team_id_from_param(self, reset_team_registry):
        """Test team_id parameter is used when provided."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        result = agent._resolve_team_id(team_id="research", metadata=None, context=None)
        assert result == "research"

    def test_team_id_from_metadata(self, reset_team_registry):
        """Test metadata.target_team is used when team_id is None."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        result = agent._resolve_team_id(
            team_id=None, metadata={"target_team": "coding"}, context=None
        )
        assert result == "coding"

    def test_fallback_to_default(self, reset_team_registry):
        """Test default team is used when no other source available."""
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        result = agent._resolve_team_id(team_id=None, metadata=None, context=None)
        assert result == "default"


class TestBaseFleetAgentBrainKwargs:
    """Tests for _build_brain_kwargs method."""

    def test_task_field_mapping(self, dummy_lm):
        """Test that message text maps to 'task' field."""
        dspy.settings.configure(lm=dummy_lm)
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        kwargs = agent._build_brain_kwargs("test input", {})
        assert kwargs.get("task") == "test input"

    def test_extra_kwargs_passed_through(self, dummy_lm):
        """Test that extra kwargs are passed through to brain when in input_fields."""
        dspy.settings.configure(lm=dummy_lm)
        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        # extra_kwargs are passed through only if their key is in input_fields
        # Since PlannerSignature has 'task', 'context', 'plan', 'reasoning'
        # custom_field would not be passed through
        kwargs = agent._build_brain_kwargs("test", {"task": "override"})
        # The task is set to message_text, not from extra_kwargs
        assert kwargs.get("task") == "test"


class TestBaseFleetAgentPayloadExtraction:
    """Tests for _extract_payload method."""

    def test_extract_payload_from_result_attr(self, dummy_lm):
        """Test extracting payload from 'result' attribute."""
        dspy.settings.configure(lm=dummy_lm)

        class MockPrediction:
            result = {"status": "success", "data": "test"}

        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        payload = agent._extract_payload(MockPrediction())
        assert payload == {"status": "success", "data": "test"}

    def test_extract_payload_model_dump(self, dummy_lm):
        """Test extracting payload from model_dump()."""
        dspy.settings.configure(lm=dummy_lm)

        class MockPrediction:
            def model_dump(self):
                return {"key": "value"}

        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        payload = agent._extract_payload(MockPrediction())
        assert payload == {"key": "value"}

    def test_extract_payload_dict_method(self, dummy_lm):
        """Test extracting payload from dict() (deprecated)."""
        dspy.settings.configure(lm=dummy_lm)

        class MockPrediction:
            def dict(self):
                return {"legacy": "value"}

        agent = BaseFleetAgent(name="Test", role="tester", brain_signature=PlannerSignature)

        payload = agent._extract_payload(MockPrediction())
        assert payload == {"legacy": "value"}


class TestBaseFleetAgentTextExtraction:
    """Tests for _extract_text static method."""

    def test_extract_text_from_chat_message(self, chat_message):
        """Test extracting text from ChatMessage."""
        text = BaseFleetAgent._extract_message_text(chat_message)
        assert text == "Hello, test!"

    def test_extract_text_from_dict(self):
        """Test extracting text from dict."""
        text = BaseFleetAgent._extract_message_text({"text": "dict text"})
        assert text == "dict text"

    def test_extract_text_from_dict_content(self):
        """Test extracting text from dict with 'content' key."""
        text = BaseFleetAgent._extract_message_text({"content": "content text"})
        assert text == "content text"

    def test_extract_text_from_str(self):
        """Test extracting text from string."""
        text = BaseFleetAgent._extract_message_text("string text")
        assert text == "string text"

    def test_extract_text_none(self):
        """Test extracting text from None returns empty string."""
        text = BaseFleetAgent._extract_message_text(None)
        assert text == ""


class TestBaseFleetAgentExecutionResult:
    """Tests for _coerce_execution_result method."""

    def test_coerce_execution_result_from_dict(self):
        """Test coercing dict to ExecutionResult."""
        from agentic_fleet.dspy_modules.signatures import ExecutionResult

        raw = {"status": "success", "content": "test", "artifacts": []}
        result = BaseFleetAgent._coerce_execution_result(raw)

        # Should either be ExecutionResult or the raw dict
        assert isinstance(result, (ExecutionResult, dict))


class TestBaseFleetAgentHistoryExtraction:
    """Tests for history extraction methods."""

    def test_extract_first_message_text(self):
        """Test extracting first message text from history."""
        messages = [
            ChatMessage(role=Role.USER, text="first"),
            ChatMessage(role=Role.ASSISTANT, text="second"),
        ]

        text = BaseFleetAgent._extract_first_message_text(messages)
        assert text == "first"

    def test_extract_last_message_text(self):
        """Test extracting last message text from history."""
        messages = [
            ChatMessage(role=Role.USER, text="first"),
            ChatMessage(role=Role.ASSISTANT, text="second"),
        ]

        text = BaseFleetAgent._extract_last_message_text(messages)
        assert text == "second"

    def test_extract_history_from_list(self):
        """Test _extract_history from list of messages."""
        messages = [ChatMessage(role=Role.USER, text="test")]

        history = BaseFleetAgent._extract_history(messages, None)
        assert len(history) == 1

    def test_extract_history_from_none(self):
        """Test _extract_history returns empty list for None."""
        history = BaseFleetAgent._extract_history(None, None)
        assert history == []
