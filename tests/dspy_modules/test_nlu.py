"""Tests for DSPyNLU module."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.dspy_modules.nlu import DSPyNLU


@pytest.fixture
def mock_dspy():
    with patch("agentic_fleet.dspy_modules.nlu.dspy") as mock:
        yield mock


def test_nlu_initialization(mock_dspy):
    """Test that DSPyNLU initializes correctly."""
    nlu = DSPyNLU()
    assert nlu._intent_classifier is None
    assert nlu._entity_extractor is None

    # Trigger lazy loading
    _ = nlu.intent_classifier
    assert nlu._intent_classifier is not None
    mock_dspy.ChainOfThought.assert_called()


def test_classify_intent(mock_dspy):
    """Test intent classification."""
    nlu = DSPyNLU()

    # Mock prediction
    mock_pred = MagicMock()
    mock_pred.intent = "test_intent"
    mock_pred.confidence = 0.95
    mock_pred.reasoning = "test reasoning"

    # Mock the chain of thought module
    mock_cot = MagicMock()
    mock_cot.return_value = mock_pred
    nlu.intent_classifier = mock_cot

    result = nlu.classify_intent("test text", ["intent1", "intent2"])

    assert result["intent"] == "test_intent"
    assert result["confidence"] == 0.95
    assert result["reasoning"] == "test reasoning"
    mock_cot.assert_called_with(text="test text", possible_intents="intent1, intent2")


def test_extract_entities(mock_dspy):
    """Test entity extraction."""
    nlu = DSPyNLU()

    # Mock prediction
    mock_pred = MagicMock()
    mock_pred.entities = [{"text": "Entity", "type": "Type", "confidence": "0.9"}]
    mock_pred.reasoning = "test reasoning"

    # Mock the chain of thought module
    mock_cot = MagicMock()
    mock_cot.return_value = mock_pred
    nlu.entity_extractor = mock_cot

    result = nlu.extract_entities("test text", ["Type1", "Type2"])

    assert len(result["entities"]) == 1
    assert result["entities"][0]["text"] == "Entity"
    mock_cot.assert_called_with(text="test text", entity_types="Type1, Type2")
