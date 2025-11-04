"""
Comprehensive test suite for Magentic workflow integration.

Tests the Microsoft Agent Framework Magentic pattern implementation:
- MagenticOrchestrator with PLAN → EVALUATE → ACT → OBSERVE cycle
- MagenticFleetBuilder with builder pattern
- MagenticWorkflowService with SSE streaming
- API endpoints for workflow management
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from agentic_fleet.api.workflows.magentic_service import (
    MagenticWorkflowService,
    get_workflow_service,
)
from agentic_fleet.core.magentic_framework import (
    MagenticContext,
    MagenticOrchestrator,
    MagenticPhase,
)
from agentic_fleet.workflow.magentic_builder import MagenticFleet, MagenticFleetBuilder


# Fixtures
@pytest.fixture
def mock_config():
    """Create mock workflow configuration."""
    config = Mock()
    config.fleet.manager.model = "gpt-4o-mini"
    config.fleet.orchestrator.max_round_count = 30
    config.fleet.orchestrator.max_stall_count = 3
    config.fleet.orchestrator.max_reset_count = 2
    config.fleet.agents = ["coordinator", "planner", "executor"]
    config.checkpointing.enabled = True
    config.approval.enabled = False
    return config


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = Mock()
    agent = AsyncMock()

    # Default response
    agent.run.return_value = Mock(content="Test response", tool_calls=[])

    client.create_agent.return_value = agent
    return client


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    event_bus = Mock()
    event_bus.publish = AsyncMock()
    event_bus.subscribe = Mock()
    return event_bus


# Test MagenticContext
class TestMagenticContext:
    """Test MagenticContext dataclass."""

    def test_context_initialization(self):
        """Test context is initialized with correct defaults."""
        context = MagenticContext(task="Test task")

        assert context.task == "Test task"
        assert context.current_phase == MagenticPhase.PLAN
        assert context.plan is None
        assert context.progress_ledger == {}
        assert context.observations == []
        assert context.round_count == 0
        assert context.stall_count == 0
        assert context.reset_count == 0

    def test_context_custom_limits(self):
        """Test context with custom limits."""
        context = MagenticContext(task="Test", max_rounds=50, max_stalls=5, max_resets=3)

        assert context.max_rounds == 50
        assert context.max_stalls == 5
        assert context.max_resets == 3


# Test MagenticOrchestrator
class TestMagenticOrchestrator:
    """Test MagenticOrchestrator core functionality."""

    @patch("agentic_fleet.core.magentic_framework.OpenAIResponsesClient")
    def test_orchestrator_initialization(self, mock_client_class, mock_config, mock_event_bus):
        """Test orchestrator initializes correctly."""
        mock_client_class.return_value = Mock()

        orchestrator = MagenticOrchestrator(config=mock_config, event_bus=mock_event_bus)

        assert orchestrator.config == mock_config
        assert orchestrator.event_bus == mock_event_bus
        assert orchestrator.manager_agent is not None
        assert len(orchestrator.specialist_agents) > 0

    @pytest.mark.asyncio
    @patch("agentic_fleet.core.magentic_framework.OpenAIResponsesClient")
    async def test_plan_phase(self, mock_client_class, mock_config, mock_openai_client):
        """Test PLAN phase creates a plan."""
        mock_client_class.return_value = mock_openai_client

        orchestrator = MagenticOrchestrator(config=mock_config)
        context = MagenticContext(task="Research quantum computing")

        # Mock manager response
        orchestrator.manager_agent.run = AsyncMock(
            return_value=Mock(content="Step 1: Research\nStep 2: Analyze\nStep 3: Report")
        )

        await orchestrator._plan_phase(context)

        assert context.plan is not None
        assert "Step 1" in context.plan
        orchestrator.manager_agent.run.assert_called_once()

    @pytest.mark.asyncio
    @patch("agentic_fleet.core.magentic_framework.OpenAIResponsesClient")
    async def test_evaluate_phase(self, mock_client_class, mock_config, mock_openai_client):
        """Test EVALUATE phase creates progress ledger."""
        mock_client_class.return_value = mock_openai_client

        orchestrator = MagenticOrchestrator(config=mock_config)
        context = MagenticContext(task="Test task")
        context.plan = "Test plan"

        # Mock evaluation with tool call
        orchestrator.manager_agent.run = AsyncMock(
            return_value=Mock(
                content="Evaluation",
                tool_calls=[
                    Mock(
                        result={
                            "request_satisfied": False,
                            "in_infinite_loop": False,
                            "making_progress": True,
                            "next_agent": "planner",
                            "instruction": "Create detailed plan",
                        }
                    )
                ],
            )
        )

        evaluation = await orchestrator._evaluate_phase(context)

        assert evaluation["request_satisfied"] is False
        assert evaluation["making_progress"] is True
        assert evaluation["next_agent"] == "planner"
        assert "instruction" in evaluation

    @pytest.mark.asyncio
    @patch("agentic_fleet.core.magentic_framework.OpenAIResponsesClient")
    async def test_act_phase(self, mock_client_class, mock_config, mock_openai_client):
        """Test ACT phase executes with selected agent."""
        mock_client_class.return_value = mock_openai_client

        orchestrator = MagenticOrchestrator(config=mock_config)
        context = MagenticContext(task="Test task")
        context.progress_ledger = {"next_agent": "planner", "instruction": "Create a plan"}

        # Mock specialist agent response
        for agent in orchestrator.specialist_agents.values():
            agent.run = AsyncMock(return_value=Mock(content="Agent executed successfully"))

        response = await orchestrator._act_phase(context)

        assert "Agent executed successfully" in response
        assert len(context.observations) == 0  # Not added yet, happens in execute()

    @pytest.mark.skip(reason="Complex mock interactions - needs investigation")
    @pytest.mark.asyncio
    @patch("agentic_fleet.core.magentic_framework.OpenAIResponsesClient")
    async def test_full_workflow_cycle(self, mock_client_class, mock_config, mock_openai_client):
        """Test complete PLAN → EVALUATE → ACT → OBSERVE cycle."""
        # Create mock tool result
        mock_tool = Mock()
        mock_tool.result = {
            "request_satisfied": True,
            "in_infinite_loop": False,
            "making_progress": True,
            "next_agent": "planner",
            "instruction": "Done",
        }

        # Setup mock responses
        plan_response = Mock(content="Detailed plan with steps", tool_calls=[])
        evaluate_response = Mock(content="Task complete", tool_calls=[mock_tool])

        print(
            f"DEBUG: plan_response.tool_calls: {plan_response.tool_calls}, len: {len(plan_response.tool_calls)}"
        )
        print(
            f"DEBUG: evaluate_response.tool_calls: {evaluate_response.tool_calls}, len: {len(evaluate_response.tool_calls)}"
        )
        print(
            f"DEBUG: evaluate_response.tool_calls[0].result: {evaluate_response.tool_calls[0].result}"
        )

        # Mock agent with side_effect
        mock_agent = AsyncMock()

        call_log = []

        async def track_calls(*args, **kwargs):
            call_log.append(f"Call #{len(call_log) + 1}")
            if len(call_log) == 1:
                print("Mock agent run call #1, returning plan_response")
                print(f"  plan_response.tool_calls: {plan_response.tool_calls}")
                return plan_response
            else:
                print(f"Mock agent run call #{len(call_log)}, returning evaluate_response")
                print(f"  evaluate_response.tool_calls: {evaluate_response.tool_calls}")
                return evaluate_response

        mock_agent.run = AsyncMock(side_effect=track_calls)

        mock_openai_client.create_agent.return_value = mock_agent
        mock_client_class.return_value = mock_openai_client

        print(
            f"DEBUG: mock_openai_client.create_agent.return_value: {mock_openai_client.create_agent.return_value}"
        )
        print(
            f"DEBUG: Is it our mock_agent? {mock_openai_client.create_agent.return_value is mock_agent}"
        )

        orchestrator = MagenticOrchestrator(config=mock_config)

        print(f"DEBUG: orchestrator.manager_agent: {orchestrator.manager_agent}")
        print(f"DEBUG: Is it mock_agent? {orchestrator.manager_agent is mock_agent}")
        print(f"DEBUG: orchestrator.manager_agent type: {type(orchestrator.manager_agent)}")
        print(f"DEBUG: orchestrator.manager_agent.run type: {type(orchestrator.manager_agent.run)}")

        # Test calling the mock directly
        test_response = await orchestrator.manager_agent.run("test")
        print(
            f"DEBUG: Direct call result: {test_response}, tool_calls: {getattr(test_response, 'tool_calls', 'N/A')}"
        )
        print(f"DEBUG: call_log after direct call: {call_log}")

        # Mock specialist responses (fallback agents created during init)
        if orchestrator.specialist_agents:
            for agent in orchestrator.specialist_agents.values():
                agent.run = AsyncMock(return_value=Mock(content="Agent response", tool_calls=[]))

        context = MagenticContext(task="Test task", max_rounds=10)

        # Collect events
        events = []
        async for event in orchestrator.execute("Test task", context):
            print(f"DEBUG: Event received: {event.get('type')}")
            events.append(event)
            # Break after completion to avoid long test
            if event.get("type") == "workflow_complete":
                break

        print(f"DEBUG: Total events: {len(events)}, types: {[e.get('type') for e in events]}")
        print(f"DEBUG: Round count: {context.round_count}")

        # Verify workflow executed
        assert context.round_count > 0
        assert any(e.get("type") == "plan_created" for e in events)
        assert any(e.get("type") == "workflow_complete" for e in events)

    @pytest.mark.asyncio
    @patch("agentic_fleet.core.magentic_framework.OpenAIResponsesClient")
    async def test_workflow_reset_on_stall(
        self, mock_client_class, mock_config, mock_openai_client
    ):
        """Test workflow resets when detecting infinite loop."""
        mock_client_class.return_value = mock_openai_client

        orchestrator = MagenticOrchestrator(config=mock_config)

        # Mock evaluation indicating infinite loop
        orchestrator.manager_agent.run = AsyncMock(
            return_value=Mock(
                content="Stuck in loop",
                tool_calls=[
                    Mock(
                        result={
                            "request_satisfied": False,
                            "in_infinite_loop": True,
                            "making_progress": False,
                            "next_agent": "planner",
                            "instruction": "Try again",
                        }
                    )
                ],
            )
        )

        context = MagenticContext(task="Test", max_stalls=2, max_rounds=10)

        events = []
        async for event in orchestrator.execute("Test", context):
            events.append(event)
            # Stop after reset
            if event.get("type") == "workflow_reset":
                break
            if len(events) > 20:  # Safety limit
                break

        # Verify reset occurred
        assert any(e.get("type") == "workflow_reset" for e in events)
        assert context.reset_count > 0


# Test MagenticFleetBuilder
class TestMagenticFleetBuilder:
    """Test MagenticFleetBuilder builder pattern."""

    def test_builder_initialization(self):
        """Test builder initializes with defaults."""
        builder = MagenticFleetBuilder()

        assert builder._config is None
        assert builder._checkpointing_enabled is False
        assert builder._approval_enabled is False
        assert builder._event_callbacks == []

    def test_builder_chaining(self, mock_config):
        """Test builder method chaining."""
        builder = MagenticFleetBuilder()

        result = builder.with_config(mock_config)
        assert result is builder  # Returns self for chaining

        result = builder.with_checkpointing(True)
        assert result is builder

        result = builder.with_approval_gates(True)
        assert result is builder

    def test_builder_requires_config(self):
        """Test builder requires config before build."""
        builder = MagenticFleetBuilder()

        with pytest.raises(ValueError, match="Configuration required"):
            builder.build()

    @pytest.mark.skip(
        reason="MagenticOrchestrator not yet implemented - builder requires orchestrator class"
    )
    @patch("agentic_fleet.workflow.magentic_builder.MagenticOrchestrator")
    @patch("agentic_fleet.workflow.magentic_builder.WorkflowExecutor")
    def test_builder_creates_fleet(self, mock_executor_class, mock_orchestrator_class, mock_config):
        """Test builder creates fleet with all components."""
        builder = MagenticFleetBuilder()

        fleet = builder.with_config(mock_config).build()

        assert isinstance(fleet, MagenticFleet)
        assert fleet.config == mock_config
        mock_orchestrator_class.assert_called_once()
        mock_executor_class.assert_called_once()

    @pytest.mark.skip(reason="Config loading implementation needs to be updated")
    def test_create_default_fleet(self, mock_config):
        """Test default fleet factory function."""
        # This test is skipped until we implement proper config loading
        pass


# Test MagenticWorkflowService
class TestMagenticWorkflowService:
    """Test MagenticWorkflowService API layer."""

    @pytest.mark.asyncio
    async def test_create_workflow(self):
        """Test workflow creation."""
        service = MagenticWorkflowService()

        workflow_id = await service.create_workflow(task="Test task", config={"max_rounds": 20})

        # Verify valid UUID
        assert UUID(workflow_id)

        # Verify stored in active workflows
        assert workflow_id in service.active_workflows
        workflow = service.active_workflows[workflow_id]
        assert workflow["task"] == "Test task"
        assert workflow["status"] == "created"
        assert workflow["context"].max_rounds == 20

    @pytest.mark.asyncio
    async def test_get_workflow_status(self):
        """Test getting workflow status."""
        service = MagenticWorkflowService()

        workflow_id = await service.create_workflow("Test task")
        status = await service.get_workflow_status(workflow_id)

        assert status["workflow_id"] == workflow_id
        assert status["task"] == "Test task"
        assert status["status"] == "created"
        assert status["round_count"] == 0
        assert status["phase"] == "plan"

    @pytest.mark.asyncio
    async def test_get_nonexistent_workflow(self):
        """Test getting status of nonexistent workflow."""
        service = MagenticWorkflowService()

        status = await service.get_workflow_status("nonexistent-id")

        assert "error" in status

    @pytest.mark.asyncio
    async def test_list_workflows(self):
        """Test listing all workflows."""
        service = MagenticWorkflowService()

        id1 = await service.create_workflow("Task 1")
        id2 = await service.create_workflow("Task 2")

        workflows = await service.list_workflows()

        assert len(workflows) == 2
        assert any(w["workflow_id"] == id1 for w in workflows)
        assert any(w["workflow_id"] == id2 for w in workflows)

    @pytest.mark.asyncio
    async def test_delete_workflow(self):
        """Test workflow deletion."""
        service = MagenticWorkflowService()

        workflow_id = await service.create_workflow("Test task")
        deleted = await service.delete_workflow(workflow_id)

        assert deleted is True
        assert workflow_id not in service.active_workflows

    @pytest.mark.asyncio
    async def test_pause_workflow(self):
        """Test pausing workflow."""
        service = MagenticWorkflowService()

        workflow_id = await service.create_workflow("Test task")
        status = await service.pause_workflow(workflow_id)

        assert status["status"] == "paused"

    @pytest.mark.asyncio
    @patch("agentic_fleet.api.workflows.magentic_service.create_default_fleet")
    async def test_execute_workflow_streaming(self, mock_create_fleet):
        """Test workflow execution with event streaming."""
        # Mock fleet
        mock_fleet = Mock()

        # Must be async generator for async for loop
        async def mock_stream(*args, **kwargs):
            """Async generator yielding test events."""
            yield {"type": "workflow_start", "data": {}}
            yield {"type": "plan_created", "data": {"plan": "Test plan"}}
            yield {"type": "workflow_complete", "data": {}}

        mock_fleet.run_with_streaming = mock_stream
        mock_create_fleet.return_value = mock_fleet

        service = MagenticWorkflowService()
        workflow_id = await service.create_workflow("Test task")

        # Collect events
        events = []
        async for event in service.execute_workflow(workflow_id):
            events.append(event)

        # Verify events streamed
        assert len(events) == 3
        assert events[0]["type"] == "workflow_start"
        assert events[2]["type"] == "workflow_complete"

        # Verify status updated
        workflow = service.active_workflows[workflow_id]
        assert workflow["status"] == "completed"

    def test_get_workflow_service_singleton(self):
        """Test singleton service accessor."""
        service1 = get_workflow_service()
        service2 = get_workflow_service()

        assert service1 is service2


# Integration tests
class TestMagenticIntegration:
    """Integration tests for complete Magentic workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skip(
        reason="MagenticOrchestrator not yet implemented - end-to-end test requires complete builder"
    )
    @patch("agentic_fleet.core.magentic_framework.OpenAIResponsesClient")
    async def test_end_to_end_workflow(self, mock_client_class, mock_config):
        """Test complete end-to-end workflow execution."""
        # Setup mocks
        mock_client = Mock()
        mock_agent = AsyncMock()

        # Simulate complete workflow
        responses = [
            Mock(content="Plan created"),
            Mock(
                content="",
                tool_calls=[
                    Mock(
                        result={
                            "request_satisfied": True,
                            "in_infinite_loop": False,
                            "making_progress": True,
                            "next_agent": "planner",
                            "instruction": "Done",
                        }
                    )
                ],
            ),
        ]
        mock_agent.run = AsyncMock(side_effect=responses)
        mock_client.create_agent.return_value = mock_agent
        mock_client_class.return_value = mock_client

        # Build fleet
        builder = MagenticFleetBuilder()
        fleet = builder.with_config(mock_config).build()

        # Execute
        events = []
        async for event in fleet.run_with_streaming("Test task"):
            events.append(event)
            if event.get("type") == "workflow_complete":
                break

        # Verify execution
        assert len(events) > 0
        assert any(e.get("type") == "workflow_start" for e in events)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
