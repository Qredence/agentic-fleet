"""Unit tests for FleetOptimizer."""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import dspy

from agentic_fleet.gepa.optimizer import FleetOptimizer, validate_judge_approval
from agentic_fleet.dspy_modules.signatures import TaskContext


class TestValidateJudgeApproval:
    """Tests for validate_judge_approval function."""

    def test_always_returns_true(self):
        """Test that validate_judge_approval always returns True."""
        example = MagicMock()
        prediction = MagicMock()

        result = validate_judge_approval(example, prediction)
        assert result is True

    def test_with_none_inputs(self):
        """Test with None inputs."""
        result = validate_judge_approval(None, None)
        assert result is True


class TestFleetOptimizer:
    """Tests for FleetOptimizer class."""

    @pytest.fixture
    def optimizer(self):
        """Create a FleetOptimizer instance."""
        return FleetOptimizer()

    def test_optimizer_creation(self):
        """Test FleetOptimizer can be instantiated."""
        optimizer = FleetOptimizer()
        assert optimizer is not None

    def test_optimizer_has_planner_optimizer(self):
        """Test FleetOptimizer has a planner_optimizer attribute."""
        optimizer = FleetOptimizer()
        assert optimizer.planner_optimizer is not None

    @pytest.mark.asyncio
    async def test_compile_creates_output_directory(self, optimizer, temp_state_dir):
        """Test that compile creates the output directory."""
        training_data = [
            dspy.Example(
                task="Task A",
                context=TaskContext(team_id="default", constraints=[], tools=[]),
                plan="Plan A",
            ).with_inputs("task", "context"),
        ]

        optimizer.compile(training_data, output_path=str(temp_state_dir))
        assert temp_state_dir.exists()

    def test_compile_saves_state_file(self, optimizer, temp_state_dir):
        """Test that compile saves state to planner_opt.json."""
        training_data = [
            dspy.Example(
                task="Task A",
                context=TaskContext(team_id="default", constraints=[], tools=[]),
                plan="Plan A",
            ).with_inputs("task", "context"),
        ]

        output_path = optimizer.compile(training_data, output_path=str(temp_state_dir))
        expected_file = temp_state_dir / "planner_opt.json"
        assert expected_file.exists()

    def test_compile_returns_path(self, optimizer, temp_state_dir):
        """Test that compile returns the Path object."""
        training_data = [
            dspy.Example(
                task="Task A",
                context=TaskContext(team_id="default", constraints=[], tools=[]),
                plan="Plan A",
            ).with_inputs("task", "context"),
        ]

        output_path = optimizer.compile(training_data, output_path=str(temp_state_dir))
        assert isinstance(output_path, Path)
        assert output_path.name == "planner_opt.json"

    def test_compile_handles_missing_context(self, optimizer, temp_state_dir):
        """Test that compile handles examples without context."""
        training_data = [
            dspy.Example(
                task="Task A",
                plan="Plan A",
            ).with_inputs("task"),
        ]

        # Should not raise
        output_path = optimizer.compile(training_data, output_path=str(temp_state_dir))
        assert output_path.exists()

    def test_compile_with_multiple_examples(self, optimizer, temp_state_dir):
        """Test compile with multiple training examples."""
        training_data = [
            dspy.Example(
                task=f"Task {i}",
                context=TaskContext(team_id="default", constraints=[], tools=[]),
                plan=f"Plan {i}",
            ).with_inputs("task", "context")
            for i in range(3)
        ]

        output_path = optimizer.compile(training_data, output_path=str(temp_state_dir))
        assert output_path.exists()


class TestOptimizeFleetFunction:
    """Tests for optimize_fleet convenience function."""

    def test_optimize_fleet_returns_path(self, temp_state_dir):
        """Test that optimize_fleet returns a Path."""
        from agentic_fleet.gepa.optimizer import optimize_fleet

        training_data = [
            dspy.Example(
                task="Task A",
                context=TaskContext(team_id="default", constraints=[], tools=[]),
                plan="Plan A",
            ).with_inputs("task", "context"),
        ]

        output_path = optimize_fleet(training_data, output_path=str(temp_state_dir))
        assert isinstance(output_path, Path)
