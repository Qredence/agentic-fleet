"""Comprehensive tests for workflows/handoff.py."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from agentic_fleet.workflows.handoff import (
    HandoffContext,
    HandoffManager,
)

# =============================================================================
# Test Data Classes (for testing purposes)
# =============================================================================


@dataclass
class MockHandoffDecision:
    """Mock handoff decision for testing (not a DSPy signature)."""

    should_handoff: bool
    next_agent: str | None = None
    handoff_context: str = ""
    handoff_reason: str = ""


def create_handoff_context(
    task: str | None, history: list[dict[str, Any]] | None, **kwargs: Any
) -> dict[str, Any]:
    """Create a handoff context dictionary.

    Args:
        task: The task being handed off
        history: List of previous agent actions
        **kwargs: Additional metadata

    Returns:
        Dictionary containing handoff context
    """
    return {
        "task": task or "",
        "history": history or [],
        **kwargs,
    }


def validate_handoff_decision(decision: MockHandoffDecision, available_agents: list[str]) -> bool:
    """Validate a handoff decision.

    Args:
        decision: The handoff decision to validate
        available_agents: List of available agent names

    Returns:
        True if the decision is valid, False otherwise
    """
    if not decision.should_handoff:
        return True  # No handoff requested is always valid

    if not available_agents:
        return False  # Can't handoff to no agents

    # Target agent must exist if specified
    return not (decision.next_agent and decision.next_agent not in available_agents)


# =============================================================================
# Test: HandoffContext
# =============================================================================


class TestHandoffContext:
    """Test suite for HandoffContext dataclass."""

    def test_handoff_context_creation(self):
        """Test creating a HandoffContext."""
        context = HandoffContext(
            from_agent="researcher",
            to_agent="analyst",
            task="Analyze data",
            work_completed="Gathered data from sources",
            artifacts={"data": "sample"},
            remaining_objectives=["Analyze trends"],
            success_criteria=["Analysis complete"],
            tool_requirements=["HostedCodeInterpreterTool"],
            estimated_effort="moderate",
            quality_checklist=["Verify data"],
            handoff_reason="Requires data analysis",
        )

        assert context.from_agent == "researcher"
        assert context.to_agent == "analyst"
        assert context.work_completed == "Gathered data from sources"
        assert context.artifacts == {"data": "sample"}

    def test_handoff_context_to_dict(self):
        """Test HandoffContext to_dict method."""
        context = HandoffContext(
            from_agent="researcher",
            to_agent="analyst",
            task="Analyze data",
            work_completed="Gathered data",
            artifacts={},
            remaining_objectives=[],
            success_criteria=[],
            tool_requirements=[],
            estimated_effort="simple",
            quality_checklist=[],
        )

        result = context.to_dict()

        assert result["from_agent"] == "researcher"
        assert result["to_agent"] == "analyst"
        assert "timestamp" in result

    def test_handoff_context_from_dict(self):
        """Test HandoffContext from_dict method."""
        data = {
            "from_agent": "researcher",
            "to_agent": "analyst",
            "task": "Test task",
            "work_completed": "Work done",
            "artifacts": {"key": "value"},
            "remaining_objectives": ["obj1"],
            "success_criteria": ["crit1"],
            "tool_requirements": ["tool1"],
            "estimated_effort": "complex",
            "quality_checklist": ["check1"],
            "metadata": {},
            "timestamp": "2025-12-07T10:00:00",
            "handoff_reason": "Testing",
        }

        context = HandoffContext.from_dict(data)

        assert context.from_agent == "researcher"
        assert context.to_agent == "analyst"
        assert context.artifacts == {"key": "value"}


# =============================================================================
# Test: MockHandoffDecision (test helper)
# =============================================================================


class TestMockHandoffDecision:
    """Test suite for MockHandoffDecision dataclass (test helper)."""

    def test_handoff_decision_creation(self):
        """Test creating a MockHandoffDecision."""
        decision = MockHandoffDecision(
            should_handoff=True,
            next_agent="analyst",
            handoff_reason="Requires data analysis",
            handoff_context="data sample",
        )

        assert decision.should_handoff is True
        assert decision.next_agent == "analyst"
        assert decision.handoff_reason == "Requires data analysis"

    def test_handoff_decision_defaults(self):
        """Test MockHandoffDecision with default values."""
        decision = MockHandoffDecision(should_handoff=False)

        assert decision.should_handoff is False
        assert decision.next_agent is None
        assert decision.handoff_reason == ""

    def test_handoff_decision_with_none_agent(self):
        """Test MockHandoffDecision with None next_agent."""
        decision = MockHandoffDecision(
            should_handoff=True,
            next_agent=None,
            handoff_reason="Code needed",
        )

        assert decision.should_handoff is True
        assert decision.next_agent is None


# =============================================================================
# Test: HandoffManager
# =============================================================================


class TestHandoffManager:
    """Test suite for HandoffManager class."""

    @pytest.fixture
    def mock_supervisor(self):
        """Create a mock DSPy supervisor."""
        supervisor = MagicMock()
        supervisor.tool_registry = None
        return supervisor

    @pytest.fixture
    def manager(self, mock_supervisor):
        """Create a HandoffManager instance."""
        return HandoffManager(dspy_supervisor=mock_supervisor)

    def test_manager_initialization(self, manager):
        """Test HandoffManager initialization."""
        assert manager.supervisor is not None
        assert manager.handoff_history == []

    def test_manager_with_compiled_supervisor_provider(self, mock_supervisor):
        """Test manager with compiled supervisor provider."""
        compiled_supervisor = MagicMock()

        def get_compiled():
            return compiled_supervisor

        manager = HandoffManager(
            dspy_supervisor=mock_supervisor,
            get_compiled_supervisor=get_compiled,
        )

        # Should prefer compiled supervisor
        result = manager._sup()
        assert result == compiled_supervisor

    @pytest.mark.asyncio
    async def test_evaluate_handoff_returns_agent_name(self, manager):
        """Test evaluate_handoff returns agent name when handoff needed."""
        # Mock the supervisor to return a handoff decision
        mock_decision = MagicMock()
        mock_decision.should_handoff = "yes"
        mock_decision.next_agent = "analyst"
        mock_decision.handoff_reason = "Analysis needed"

        # Mock _sup() to return a supervisor with handoff_decision method
        mock_sup = MagicMock()
        mock_sup.handoff_decision = MagicMock(return_value=mock_decision)
        manager._sup = MagicMock(return_value=mock_sup)

        result = await manager.evaluate_handoff(
            current_agent="researcher",
            work_completed="Data gathered",
            remaining_work="Analysis needed",
            available_agents={"analyst": "Data analysis specialist"},
        )

        assert result == "analyst"

    @pytest.mark.asyncio
    async def test_evaluate_handoff_returns_none_when_not_needed(self, manager):
        """Test evaluate_handoff returns None when no handoff needed."""
        mock_decision = MagicMock()
        mock_decision.should_handoff = "no"
        mock_decision.next_agent = ""

        # Mock _sup() to return a supervisor with handoff_decision method
        mock_sup = MagicMock()
        mock_sup.handoff_decision = MagicMock(return_value=mock_decision)
        manager._sup = MagicMock(return_value=mock_sup)

        result = await manager.evaluate_handoff(
            current_agent="researcher",
            work_completed="Task complete",
            remaining_work="",
            available_agents={"analyst": "Data analysis"},
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_handoff_with_empty_agents(self, manager):
        """Test evaluate_handoff with no available agents."""
        result = await manager.evaluate_handoff(
            current_agent="researcher",
            work_completed="Work done",
            remaining_work="More work",
            available_agents={},
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_handoff_package(self, manager):
        """Test creating a handoff package."""
        mock_protocol = MagicMock()
        mock_protocol.quality_checklist = "- Check 1\n- Check 2"
        mock_protocol.estimated_effort = "moderate"
        mock_protocol.handoff_package = "Package content"

        # Mock _sup() to return a supervisor with handoff_protocol method
        mock_sup = MagicMock()
        mock_sup.handoff_protocol = MagicMock(return_value=mock_protocol)
        manager._sup = MagicMock(return_value=mock_sup)

        result = await manager.create_handoff_package(
            from_agent="researcher",
            to_agent="analyst",
            work_completed="Data gathered",
            artifacts={"data": [1, 2, 3]},
            remaining_objectives=["Analyze data"],
            task="Full analysis",
        )

        assert isinstance(result, HandoffContext)
        assert result.from_agent == "researcher"
        assert result.to_agent == "analyst"
        assert "Check 1" in result.quality_checklist

    @pytest.mark.asyncio
    async def test_create_handoff_package_fallback_on_error(self, manager):
        """Test handoff package creation falls back on error."""
        # Mock _sup() to return a supervisor that raises an exception
        mock_sup = MagicMock()
        mock_sup.handoff_protocol = MagicMock(side_effect=Exception("Protocol failed"))
        manager._sup = MagicMock(return_value=mock_sup)

        result = await manager.create_handoff_package(
            from_agent="researcher",
            to_agent="analyst",
            work_completed="Work done",
            artifacts={},
            remaining_objectives=["Objective"],
        )

        # Should return minimal fallback context
        assert isinstance(result, HandoffContext)
        assert result.estimated_effort == "moderate"

    @pytest.mark.asyncio
    async def test_assess_handoff_quality(self, manager):
        """Test assessing handoff quality."""
        mock_assessment = MagicMock()
        mock_assessment.handoff_quality_score = "8.5"
        mock_assessment.context_completeness = "yes"
        mock_assessment.success_factors = "Good context"
        mock_assessment.improvement_areas = "None"

        # Mock _sup() to return a supervisor with handoff_quality_assessor method
        mock_sup = MagicMock()
        mock_sup.handoff_quality_assessor = MagicMock(return_value=mock_assessment)
        manager._sup = MagicMock(return_value=mock_sup)

        context = HandoffContext(
            from_agent="researcher",
            to_agent="analyst",
            task="Test",
            work_completed="Done",
            artifacts={},
            remaining_objectives=[],
            success_criteria=[],
            tool_requirements=[],
            estimated_effort="simple",
            quality_checklist=[],
        )

        result = await manager.assess_handoff_quality(
            handoff_context=context,
            work_after_handoff="Analysis complete",
        )

        assert result["quality_score"] == 8.5
        assert result["context_complete"] is True


# =============================================================================
# Test: create_handoff_context Helper
# =============================================================================


class TestCreateHandoffContext:
    """Test suite for create_handoff_context function."""

    def test_create_handoff_context_basic(self):
        """Test creating basic handoff context."""
        task = "Analyze sales data"
        history = [{"agent": "researcher", "action": "gathered data"}]

        context = create_handoff_context(task, history)

        assert "task" in context
        assert "history" in context
        assert context["task"] == task
        assert context["history"] == history

    def test_create_handoff_context_with_metadata(self):
        """Test creating context with additional metadata."""
        task = "Code review"
        history: list[dict[str, Any]] = []

        context = create_handoff_context(task, history, urgency="high", expertise="security")

        assert context["urgency"] == "high"
        assert context["expertise"] == "security"

    def test_create_handoff_context_empty_history(self):
        """Test context creation with empty history."""
        task = "New task"
        context = create_handoff_context(task, [])

        assert context["task"] == task
        assert context["history"] == []

    def test_create_handoff_context_with_none_values(self):
        """Test context creation with None values."""
        context = create_handoff_context(None, None)

        assert context["task"] == ""
        assert context["history"] == []


# =============================================================================
# Test: validate_handoff_decision Helper
# =============================================================================


class TestValidateHandoffDecision:
    """Test suite for validate_handoff_decision function."""

    def test_validate_valid_decision(self):
        """Test validation of valid handoff decision."""
        decision = MockHandoffDecision(
            should_handoff=True,
            next_agent="analyst",
            handoff_reason="Analysis needed",
        )
        available_agents = ["researcher", "analyst", "writer"]

        is_valid = validate_handoff_decision(decision, available_agents)

        assert is_valid is True

    def test_validate_decision_with_invalid_target(self):
        """Test validation with invalid target agent."""
        decision = MockHandoffDecision(
            should_handoff=True,
            next_agent="nonexistent",
            handoff_reason="Invalid",
        )
        available_agents = ["researcher", "analyst"]

        is_valid = validate_handoff_decision(decision, available_agents)

        assert is_valid is False

    def test_validate_decision_no_handoff(self):
        """Test validation when no handoff is requested."""
        decision = MockHandoffDecision(should_handoff=False)
        available_agents = ["researcher", "analyst"]

        is_valid = validate_handoff_decision(decision, available_agents)

        assert is_valid is True

    def test_validate_decision_with_empty_agent_list(self):
        """Test validation with empty available agents list."""
        decision = MockHandoffDecision(
            should_handoff=True,
            next_agent="analyst",
        )
        available_agents: list[str] = []

        is_valid = validate_handoff_decision(decision, available_agents)

        assert is_valid is False


# =============================================================================
# Test: HandoffManager Edge Cases
# =============================================================================


class TestHandoffManagerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def manager(self):
        """Create a HandoffManager instance."""
        mock_supervisor = MagicMock()
        mock_supervisor.tool_registry = None
        return HandoffManager(dspy_supervisor=mock_supervisor)

    @pytest.mark.asyncio
    async def test_concurrent_handoff_evaluations(self, manager):
        """Test handling concurrent handoff evaluations."""
        mock_decision = MagicMock()
        mock_decision.should_handoff = "no"
        mock_decision.next_agent = ""

        manager.handoff_decision_module = MagicMock(return_value=mock_decision)

        # Simulate concurrent handoff evaluations
        tasks = [
            manager.evaluate_handoff(
                "agent1",
                "work1",
                "remaining1",
                {"agent2": "Agent 2"},
            ),
            manager.evaluate_handoff(
                "agent1",
                "work2",
                "remaining2",
                {"agent2": "Agent 2"},
            ),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 2

    def test_handoff_history_tracking(self, manager):
        """Test that handoff history is tracked."""
        assert manager.handoff_history == []

        # After creating handoff packages, history should be updated
        # (tested via create_handoff_package)

    def test_get_handoff_summary_empty(self, manager):
        """Test getting summary with empty history."""
        summary = manager.get_handoff_summary()

        assert summary["total_handoffs"] == 0
        assert summary["handoff_pairs"] == {}

    def test_clear_history(self, manager):
        """Test clearing handoff history."""
        # Add some mock history
        manager.handoff_history.append(
            HandoffContext(
                from_agent="a",
                to_agent="b",
                task="t",
                work_completed="w",
                artifacts={},
                remaining_objectives=[],
                success_criteria=[],
                tool_requirements=[],
                estimated_effort="simple",
                quality_checklist=[],
            )
        )

        manager.clear_history()

        assert manager.handoff_history == []


# =============================================================================
# Test: HandoffManager Statistics
# =============================================================================


class TestHandoffManagerStatistics:
    """Test HandoffManager statistics and reporting."""

    @pytest.fixture
    def manager_with_history(self):
        """Create a manager with handoff history."""
        mock_supervisor = MagicMock()
        mock_supervisor.tool_registry = None
        manager = HandoffManager(dspy_supervisor=mock_supervisor)

        # Add some handoff history
        for i in range(3):
            manager.handoff_history.append(
                HandoffContext(
                    from_agent="researcher",
                    to_agent="analyst",
                    task=f"Task {i}",
                    work_completed="Work done",
                    artifacts={},
                    remaining_objectives=[],
                    success_criteria=[],
                    tool_requirements=[],
                    estimated_effort="moderate",
                    quality_checklist=[],
                )
            )

        return manager

    def test_get_handoff_summary_with_history(self, manager_with_history):
        """Test getting summary with history."""
        summary = manager_with_history.get_handoff_summary()

        assert summary["total_handoffs"] == 3
        assert "researcher → analyst" in summary["handoff_pairs"]
        assert summary["handoff_pairs"]["researcher → analyst"] == 3

    def test_effort_distribution(self, manager_with_history):
        """Test effort distribution in summary."""
        summary = manager_with_history.get_handoff_summary()

        assert "effort_distribution" in summary
        assert summary["effort_distribution"]["moderate"] == 3
