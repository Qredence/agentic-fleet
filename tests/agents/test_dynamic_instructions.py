from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.agents.coordinator import AgentFactory


@pytest.fixture
def mock_dspy_generator():
    generator = MagicMock()
    generator.return_value.agent_instructions = "Dynamic Instructions"
    return generator


def test_planner_dynamic_instructions(mock_dspy_generator):
    with patch(
        "agentic_fleet.agents.coordinator.dspy.ChainOfThought", return_value=mock_dspy_generator
    ):
        factory = AgentFactory()
        # Force enable DSPy
        factory.enable_dspy = True
        factory.instruction_generator = mock_dspy_generator

        instructions = factory._resolve_instructions("prompts.planner")

        assert instructions == "Dynamic Instructions"
        mock_dspy_generator.assert_called_once()


def test_planner_fallback_on_error(mock_dspy_generator):
    mock_dspy_generator.side_effect = Exception("DSPy Error")

    with patch(
        "agentic_fleet.agents.coordinator.dspy.ChainOfThought", return_value=mock_dspy_generator
    ):
        factory = AgentFactory()
        factory.enable_dspy = True
        factory.instruction_generator = mock_dspy_generator

        # Should fallback to static prompts
        instructions = factory._resolve_instructions("prompts.planner")

        assert "You are the Orchestrator" in instructions
        mock_dspy_generator.assert_called_once()


def test_other_agent_static_instructions():
    factory = AgentFactory()
    instructions = factory._resolve_instructions("prompts.coder")
    assert "You are the coder" in instructions
