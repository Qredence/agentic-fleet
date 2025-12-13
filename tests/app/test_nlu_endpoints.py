"""Tests for NLU API endpoints."""

from unittest.mock import MagicMock

import pytest

from agentic_fleet.dspy_modules.nlu import DSPyNLU


@pytest.fixture
def mock_workflow():
    """Mock the SupervisorWorkflow dependency."""
    mock_wf = MagicMock()
    mock_wf.dspy_reasoner = MagicMock()

    # Mock DSPyNLU
    mock_nlu = MagicMock(spec=DSPyNLU)
    mock_nlu.classify_intent.return_value = {
        "intent": "test_intent",
        "confidence": 0.95,
        "reasoning": "test reasoning",
    }
    mock_nlu.extract_entities.return_value = {
        "entities": [{"text": "Entity", "type": "Type", "confidence": "0.9"}],
        "reasoning": "test reasoning",
    }

    mock_wf.dspy_reasoner.nlu = mock_nlu

    # Override dependency
    from agentic_fleet.api.deps import get_workflow
    from agentic_fleet.main import app

    app.dependency_overrides[get_workflow] = lambda: mock_wf

    yield mock_wf

    app.dependency_overrides = {}


def test_classify_intent_endpoint(client, mock_workflow: MagicMock) -> None:
    """Test POST /api/v1/classify_intent."""
    response = client.post(
        "/api/v1/classify_intent",
        json={"text": "test text", "possible_intents": ["intent1", "intent2"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "test_intent"
    assert data["confidence"] == 0.95
    assert data["reasoning"] == "test reasoning"

    mock_workflow.dspy_reasoner.nlu.classify_intent.assert_called_once_with(
        text="test text", possible_intents=["intent1", "intent2"]
    )


def test_extract_entities_endpoint(client, mock_workflow: MagicMock) -> None:
    """Test POST /api/v1/extract_entities."""
    response = client.post(
        "/api/v1/extract_entities", json={"text": "test text", "entity_types": ["Type1", "Type2"]}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]) == 1
    assert data["entities"][0]["text"] == "Entity"
    assert data["reasoning"] == "test reasoning"

    mock_workflow.dspy_reasoner.nlu.extract_entities.assert_called_once_with(
        text="test text", entity_types=["Type1", "Type2"]
    )
