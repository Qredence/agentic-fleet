"""Tests for DSPyNLU module."""

from unittest.mock import MagicMock

import dspy
import pytest

from agentic_fleet.dspy_modules.nlu import _MODULE_CACHE, DSPyNLU


@pytest.fixture(autouse=True)
def clear_module_cache():
    """Clear the module cache before each test."""
    _MODULE_CACHE.clear()


@pytest.fixture(autouse=True)
def enable_fake_dspy_lm(monkeypatch):
    """Ensure DSPyNLU tests exercise the non-short-circuit path.

    The test suite globally disables external LLM calls by setting
    `dspy.settings.lm=None`. These unit tests fully mock the NLU predictors,
    so we can safely set a dummy LM to bypass the early-return guard without
    touching the network.
    """

    monkeypatch.setattr(dspy.settings, "lm", MagicMock(), raising=False)
    yield
    _MODULE_CACHE.clear()


def test_nlu_initialization():
    """Test that DSPyNLU initializes correctly."""
    nlu = DSPyNLU()
    assert nlu._intent_classifier is None
    assert nlu._entity_extractor is None

    # Manually set a mock intent classifier to test lazy loading
    mock_ic = MagicMock()
    nlu._intent_classifier = mock_ic

    # Verify lazy loading returns our mock
    result = nlu.intent_classifier
    assert result == mock_ic


def test_classify_intent():
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
    nlu._intent_classifier = mock_cot
    nlu._modules_initialized = True  # Skip lazy init

    result = nlu.classify_intent("test text", ["intent1", "intent2"])

    assert result["intent"] == "test_intent"
    assert result["confidence"] == 0.95
    assert result["reasoning"] == "test reasoning"
    mock_cot.assert_called_with(text="test text", possible_intents="intent1, intent2")


def test_extract_entities():
    """Test entity extraction."""
    nlu = DSPyNLU()

    # Mock prediction
    mock_pred = MagicMock()
    mock_pred.entities = [{"text": "Entity", "type": "Type", "confidence": "0.9"}]
    mock_pred.reasoning = "test reasoning"

    # Mock the chain of thought module
    mock_cot = MagicMock()
    mock_cot.return_value = mock_pred
    nlu._entity_extractor = mock_cot
    nlu._modules_initialized = True  # Skip lazy init

    result = nlu.extract_entities("test text", ["Type1", "Type2"])

    assert len(result["entities"]) == 1
    assert result["entities"][0]["text"] == "Entity"
    mock_cot.assert_called_with(text="test text", entity_types="Type1, Type2")
