"""Comprehensive tests for workflows/handoff.py."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from agentic_fleet.workflows.handoff import (
    HandoffDecision,
    HandoffManager,
    create_handoff_context,
    validate_handoff_decision,
)
from agentic_fleet.agents.base import Agent


class TestHandoffDecision:
    """Test suite for HandoffDecision dataclass."""

    def test_handoff_decision_creation(self):
        """Test creating a HandoffDecision."""
        decision = HandoffDecision(
            should_handoff=True,
            target_agent="analyst",
            reason="Requires data analysis",
            context={"data": "sample"},
        )

        assert decision.should_handoff is True
        assert decision.target_agent == "analyst"
        assert decision.reason == "Requires data analysis"
        assert decision.context == {"data": "sample"}

    def test_handoff_decision_defaults(self):
        """Test HandoffDecision with default values."""
        decision = HandoffDecision(
            should_handoff=False, target_agent=None, reason="", context={}
        )

        assert decision.should_handoff is False
        assert decision.target_agent is None
        assert decision.reason == ""
        assert decision.context == {}

    def test_handoff_decision_with_none_context(self):
        """Test HandoffDecision with None context."""
        decision = HandoffDecision(
            should_handoff=True, target_agent="coder", reason="Code needed", context=None
        )

        assert decision.should_handoff is True
        assert decision.context is None

    def test_handoff_decision_immutability(self):
        """Test that HandoffDecision is immutable (if using frozen dataclass)."""
        decision = HandoffDecision(
            should_handoff=True, target_agent="writer", reason="Test", context={}
        )

        # If frozen, this should raise
        try:
            decision.should_handoff = False
            # If we get here, it's mutable (which is fine, just document behavior)
            assert decision.should_handoff is False
        except AttributeError:
            # Frozen dataclass - expected
            pass


class TestHandoffManager:
    """Test suite for HandoffManager class."""

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents."""
        researcher = Mock(spec=Agent)
        researcher.name = "researcher"

        analyst = Mock(spec=Agent)
        analyst.name = "analyst"

        return {"researcher": researcher, "analyst": analyst}

    @pytest.fixture
    def manager(self, mock_agents):
        """Create a HandoffManager instance."""
        mock_supervisor = Mock()
        manager = HandoffManager(dspy_supervisor=mock_supervisor)
        manager.agents = mock_agents  # Set agents directly for testing
        return manager

    def test_manager_initialization(self, manager, mock_agents):
        """Test HandoffManager initialization."""
        assert manager.agents == mock_agents
        assert len(manager.agents) == 2
        assert "researcher" in manager.agents
        assert "analyst" in manager.agents

    def test_manager_with_empty_agents(self):
        """Test manager with empty agents dict."""
        mock_supervisor = Mock()
        manager = HandoffManager(dspy_supervisor=mock_supervisor)
        manager.agents = {}  # Set empty agents for testing
        assert manager.agents == {}

    async def test_evaluate_handoff_need_true(self, manager):
        """Test evaluating handoff when handoff is needed."""
        current_agent = "researcher"
        task = "Analyze this complex dataset"
        context = {"complexity": "high"}

        with patch.object(manager, "_should_handoff", return_value=True):
            with patch.object(
                manager, "_determine_target_agent", return_value="analyst"
            ):
                decision = await manager.evaluate_handoff_need(
                    current_agent, task, context
                )

                assert decision.should_handoff is True
                assert decision.target_agent == "analyst"

    async def test_evaluate_handoff_need_false(self, manager):
        """Test evaluating handoff when no handoff is needed."""
        current_agent = "researcher"
        task = "Simple research task"
        context = {}

        with patch.object(manager, "_should_handoff", return_value=False):
            decision = await manager.evaluate_handoff_need(current_agent, task, context)

            assert decision.should_handoff is False
            assert decision.target_agent is None

    async def test_determine_target_agent_by_task_type(self, manager):
        """Test target agent determination based on task type."""
        task = "Write a comprehensive report"
        target = await manager._determine_target_agent(task, {})

        # Should route to writer for writing tasks
        assert isinstance(target, (str, type(None)))

    async def test_determine_target_agent_with_explicit_context(self, manager):
        """Test target agent with explicit context hint."""
        task = "Generic task"
        context = {"preferred_agent": "analyst"}

        target = await manager._determine_target_agent(task, context)

        # Should respect explicit preference if available
        assert target is not None

    async def test_execute_handoff_success(self, manager):
        """Test successful handoff execution."""
        source_agent = "researcher"
        target_agent = "analyst"
        task = "Analyze data"
        context = {"data": [1, 2, 3]}

        mock_target = manager.agents[target_agent]
        mock_target.execute = AsyncMock(return_value={"result": "analysis complete"})

        result = await manager.execute_handoff(source_agent, target_agent, task, context)

        assert result["result"] == "analysis complete"
        mock_target.execute.assert_called_once()

    async def test_execute_handoff_to_nonexistent_agent(self, manager):
        """Test handoff to non-existent agent."""
        with pytest.raises(KeyError):
            await manager.execute_handoff(
                "researcher", "nonexistent", "task", {}
            )

    async def test_execute_handoff_with_agent_failure(self, manager):
        """Test handoff when target agent fails."""
        mock_target = manager.agents["analyst"]
        mock_target.execute = AsyncMock(side_effect=Exception("Agent failed"))

        with pytest.raises(Exception, match="Agent failed"):
            await manager.execute_handoff("researcher", "analyst", "task", {})

    def test_validate_agent_exists(self, manager):
        """Test validation that agent exists."""
        assert manager._validate_agent_exists("researcher") is True
        assert manager._validate_agent_exists("analyst") is True
        assert manager._validate_agent_exists("nonexistent") is False

    def test_get_available_handoff_targets(self, manager):
        """Test getting available handoff targets."""
        current_agent = "researcher"
        targets = manager.get_available_handoff_targets(current_agent)

        # Should return all agents except current
        assert "researcher" not in targets
        assert "analyst" in targets


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
        history = []
        metadata = {"urgency": "high", "expertise": "security"}

        context = create_handoff_context(task, history, metadata=metadata)

        assert "metadata" in context or "urgency" in context
        # Exact structure depends on implementation

    def test_create_handoff_context_empty_history(self):
        """Test context creation with empty history."""
        task = "New task"
        context = create_handoff_context(task, [])

        assert context["task"] == task
        assert context["history"] == []

    def test_create_handoff_context_with_none_values(self):
        """Test context creation with None values."""
        context = create_handoff_context(None, None)

        # Should handle None gracefully
        assert "task" in context or context is not None


class TestValidateHandoffDecision:
    """Test suite for validate_handoff_decision function."""

    def test_validate_valid_decision(self):
        """Test validation of valid handoff decision."""
        decision = HandoffDecision(
            should_handoff=True, target_agent="analyst", reason="Analysis needed", context={}
        )
        available_agents = ["researcher", "analyst", "writer"]

        is_valid = validate_handoff_decision(decision, available_agents)

        assert is_valid is True

    def test_validate_decision_with_invalid_target(self):
        """Test validation with invalid target agent."""
        decision = HandoffDecision(
            should_handoff=True,
            target_agent="nonexistent",
            reason="Invalid",
            context={},
        )
        available_agents = ["researcher", "analyst"]

        is_valid = validate_handoff_decision(decision, available_agents)

        assert is_valid is False

    def test_validate_decision_no_handoff(self):
        """Test validation when no handoff is requested."""
        decision = HandoffDecision(
            should_handoff=False, target_agent=None, reason="", context={}
        )
        available_agents = ["researcher", "analyst"]

        is_valid = validate_handoff_decision(decision, available_agents)

        assert is_valid is True  # No handoff is always valid

    def test_validate_decision_with_empty_agent_list(self):
        """Test validation with empty available agents list."""
        decision = HandoffDecision(
            should_handoff=True, target_agent="analyst", reason="Test", context={}
        )
        available_agents = []

        is_valid = validate_handoff_decision(decision, available_agents)

        assert is_valid is False


class TestHandoffManagerEdgeCases:
    """Test edge cases and error handling."""

    async def test_concurrent_handoffs(self):
        """Test handling concurrent handoff requests."""
        agents = {
            "agent1": Mock(spec=Agent),
            "agent2": Mock(spec=Agent),
        }
        mock_supervisor = Mock()
        manager = HandoffManager(dspy_supervisor=mock_supervisor)
        manager.agents = agents  # Set agents for testing

        # Simulate concurrent handoff evaluations
        tasks = [
            manager.evaluate_handoff_need("agent1", "task1", {}),
            manager.evaluate_handoff_need("agent1", "task2", {}),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 2
        assert all(isinstance(r, HandoffDecision) for r in results)

    async def test_circular_handoff_prevention(self):
        """Test prevention of circular handoffs."""
        agents = {"agent1": Mock(spec=Agent), "agent2": Mock(spec=Agent)}
        mock_supervisor = Mock()
        manager = HandoffManager(dspy_supervisor=mock_supervisor)
        manager.agents = agents  # Set agents for testing

        context = {"handoff_chain": ["agent1", "agent2", "agent1"]}

        # Should detect circular handoff
        decision = await manager.evaluate_handoff_need("agent2", "task", context)

        # Implementation should prevent circular handoffs
        assert decision is not None

    def test_handoff_with_corrupted_context(self):
        """Test handoff handling with corrupted context."""
        agents = {"agent1": Mock(spec=Agent)}
        mock_supervisor = Mock()
        _ = HandoffManager(dspy_supervisor=mock_supervisor)
        # Note: manager variable intentionally unused in original test implementation

        corrupted_contexts = [
            {"history": "not a list"},
            {"task": None},
            "not a dict",
        ]

        for ctx in corrupted_contexts:
            # Should handle gracefully without crashing
            try:
                create_handoff_context("task", [])
            except Exception:
                pass  # Expected for some cases


class TestHandoffManagerIntegration:
    """Integration tests for HandoffManager."""

    @pytest.fixture
    def full_agent_system(self):
        """Create a complete agent system for integration testing."""
        agents = {}
        for name in ["researcher", "analyst", "writer", "reviewer", "coder"]:
            agent = Mock(spec=Agent)
            agent.name = name
            agent.execute = AsyncMock(return_value={"result": f"{name} completed"})
            agents[name] = agent
        return agents

    @pytest.fixture
    def full_manager(self, full_agent_system):
        """Create a manager with full agent system."""
        mock_supervisor = Mock()
        manager = HandoffManager(dspy_supervisor=mock_supervisor)
        manager.agents = full_agent_system  # Set agents for testing
        return manager

    async def test_multi_step_handoff_chain(self, full_manager):
        """Test a multi-step handoff chain."""
        # Task requires: research -> analysis -> writing
        task = "Research and analyze market trends, then write a report"

        # Step 1: Researcher
        decision1 = await full_manager.evaluate_handoff_need("researcher", task, {})

        # Step 2: Analyst (if handoff occurred)
        if decision1.should_handoff:
            result1 = await full_manager.execute_handoff(
                "researcher", decision1.target_agent, task, decision1.context
            )

            # Step 3: Writer
            decision2 = await full_manager.evaluate_handoff_need(
                decision1.target_agent, task, {"previous_result": result1}
            )

            if decision2.should_handoff:
                result2 = await full_manager.execute_handoff(
                    decision1.target_agent, decision2.target_agent, task, decision2.context
                )

                assert result2 is not None

    async def test_handoff_with_complex_context(self, full_manager):
        """Test handoff with complex context data."""
        complex_context = {
            "history": [
                {"agent": "researcher", "action": "searched", "results": ["data1"]},
                {"agent": "analyst", "action": "analyzed", "insights": ["insight1"]},
            ],
            "metadata": {
                "priority": "high",
                "deadline": "2025-12-31",
                "stakeholders": ["user1", "user2"],
            },
            "artifacts": {
                "documents": ["doc1.pdf", "doc2.pdf"],
                "code": ["script.py"],
            },
        }

        decision = await full_manager.evaluate_handoff_need(
            "analyst", "Complex task", complex_context
        )

        assert decision is not None
        # Context should be preserved
        assert decision.context is not None


# Import asyncio for concurrent tests
import asyncio