"""Test DSPy + agent-framework integration."""

from unittest.mock import AsyncMock, Mock

import pytest
from agent_framework import ChatMessage, Role
from agent_framework.openai import OpenAIResponsesClient

from agentic_fleet.agents.base import DSPyEnhancedAgent
from agentic_fleet.utils.cache import _generate_cache_key, cache_agent_response
from agentic_fleet.utils.telemetry import ExecutionMetrics, PerformanceTracker


class TestDSPyEnhancedAgent:
    """Test DSPy-enhanced agent functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock OpenAI client."""
        client = Mock(spec=OpenAIResponsesClient)
        client.model_id = "gpt-4o-mini"
        return client

    @pytest.fixture
    def basic_agent(self, mock_client):
        """Create basic DSPy-enhanced agent."""
        return DSPyEnhancedAgent(
            name="TestAgent",
            chat_client=mock_client,
            instructions="Test agent",
            enable_dspy=False,  # Disable for basic tests
            timeout=30,
        )

    def test_agent_initialization(self, basic_agent):
        """Test agent initializes correctly."""
        assert basic_agent.name == "TestAgent"
        assert basic_agent.timeout == 30
        assert basic_agent.cache_ttl == 3600
        assert basic_agent.enable_dspy is False

    def test_agent_role_description(self, basic_agent):
        """Test getting agent role description."""
        role = basic_agent._get_agent_role_description()
        assert "Test agent" in role

    def test_timeout_response(self, basic_agent):
        """Test timeout response generation."""
        response = basic_agent._create_timeout_response(30)
        assert response.role == Role.ASSISTANT
        assert "30s" in response.text
        # Metadata is stored in additional_properties in ChatMessage
        assert (
            response.additional_properties.get("metadata", {}).get("status") == "timeout"
            or response.additional_properties.get("status") == "timeout"
        )

    def test_performance_stats_empty(self, basic_agent):
        """Test performance stats with no executions."""
        stats = basic_agent.get_performance_stats()
        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_execute_without_dspy(self, basic_agent):
        """Test execution without DSPy enhancement."""
        # Mock the run method
        mock_message = ChatMessage(role=Role.ASSISTANT, text="Test response")
        basic_agent.run = AsyncMock(return_value=mock_message)

        result = await basic_agent.execute_with_timeout("test task")

        assert result.text == "Test response"
        basic_agent.run.assert_called_once()


class TestCaching:
    """Test caching functionality."""

    def test_generate_cache_key(self):
        """Test cache key generation."""
        key1 = _generate_cache_key("task1", "agent1")
        key2 = _generate_cache_key("task1", "agent1")
        key3 = _generate_cache_key("task2", "agent1")

        # Same inputs should generate same key
        assert key1 == key2

        # Different inputs should generate different keys
        assert key1 != key3

        # Keys should be valid MD5 hashes
        assert len(key1) == 32
        assert key1.isalnum()

    def test_cache_decorator_structure(self):
        """Test cache decorator can be applied."""

        @cache_agent_response(ttl=60)
        async def test_func(self, task: str):
            return f"Response to {task}"

        assert callable(test_func)


class TestPerformanceTracker:
    """Test performance tracking."""

    @pytest.fixture
    def tracker(self):
        """Create performance tracker."""
        return PerformanceTracker()

    def test_tracker_initialization(self, tracker):
        """Test tracker initializes empty."""
        assert len(tracker.executions) == 0
        assert len(tracker.metrics_by_agent) == 0

    def test_record_execution(self, tracker):
        """Test recording an execution."""
        tracker.record_execution(
            agent_name="TestAgent", duration=5.5, success=True, metadata={"test": "data"}
        )

        assert len(tracker.executions) == 1
        assert tracker.executions[0].agent_name == "TestAgent"
        assert tracker.executions[0].duration == 5.5
        assert tracker.executions[0].success is True

    def test_get_stats(self, tracker):
        """Test getting statistics."""
        # Record some executions
        tracker.record_execution("Agent1", 5.0, True)
        tracker.record_execution("Agent1", 10.0, True)
        tracker.record_execution("Agent1", 15.0, False)

        stats = tracker.get_stats("Agent1")

        assert stats["total_executions"] == 3
        assert stats["success_rate"] == pytest.approx(2 / 3)
        assert stats["avg_duration"] == pytest.approx(10.0)
        assert stats["min_duration"] == 5.0
        assert stats["max_duration"] == 15.0

    def test_get_stats_empty(self, tracker):
        """Test stats with no executions."""
        stats = tracker.get_stats("NonExistent")

        assert stats["total_executions"] == 0
        assert stats["avg_duration"] == 0.0

    def test_get_bottlenecks(self, tracker):
        """Test identifying bottlenecks."""
        # Record fast and slow executions
        tracker.record_execution("FastAgent", 2.0, True)
        tracker.record_execution("SlowAgent", 15.0, True)
        tracker.record_execution("VerySlow", 30.0, True)

        # Get bottlenecks over 5 seconds
        bottlenecks = tracker.get_bottlenecks(threshold=5.0)

        assert len(bottlenecks) == 2
        # Should be sorted by duration descending
        assert bottlenecks[0]["duration"] == 30.0
        assert bottlenecks[1]["duration"] == 15.0

    def test_execution_metrics_dataclass(self):
        """Test ExecutionMetrics dataclass."""

        metrics = ExecutionMetrics(
            agent_name="TestAgent",
            duration=5.5,
            success=True,
            metadata={"key": "value"},
            error=None,
        )

        assert metrics.agent_name == "TestAgent"
        assert metrics.duration == 5.5
        assert metrics.success is True
        assert metrics.metadata == {"key": "value"}
        assert metrics.error is None
        assert metrics.timestamp > 0  # Should have timestamp


class TestIntegration:
    """Integration tests for DSPy + agent-framework."""

    @pytest.fixture
    def mock_client(self):
        """Create mock client."""
        client = Mock(spec=OpenAIResponsesClient)
        client.model_id = "gpt-4o-mini"
        return client

    @pytest.mark.asyncio
    async def test_full_execution_flow(self, mock_client):
        """Test complete execution flow."""
        agent = DSPyEnhancedAgent(
            name="IntegrationAgent", chat_client=mock_client, enable_dspy=False, timeout=30
        )

        # Mock the run method
        mock_response = ChatMessage(role=Role.ASSISTANT, text="Integration test response")
        agent.run = AsyncMock(return_value=mock_response)

        # Execute
        result = await agent.execute_with_timeout("test task")

        # Verify
        assert result.text == "Integration test response"

        # Check performance tracking
        stats = agent.get_performance_stats()
        assert stats["total_executions"] == 1
        assert stats["success_rate"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
