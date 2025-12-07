"""Comprehensive tests for utils/types.py."""

from datetime import datetime

import pytest

from agentic_fleet.utils.types import (
    AgentMessage,
    AgentRole,
    ExecutionMode,
    TaskResult,
    TaskStatus,
    ToolResult,
    WorkflowState,
)


class TestExecutionMode:
    """Test suite for ExecutionMode enum."""

    def test_execution_mode_values(self):
        """Test all ExecutionMode enum values."""
        assert ExecutionMode.AUTO.value == "auto"
        assert ExecutionMode.DELEGATED.value == "delegated"
        assert ExecutionMode.SEQUENTIAL.value == "sequential"
        assert ExecutionMode.PARALLEL.value == "parallel"
        assert ExecutionMode.HANDOFF.value == "handoff"
        assert ExecutionMode.DISCUSSION.value == "discussion"
        assert ExecutionMode.GROUP_CHAT.value == "group_chat"

    def test_execution_mode_from_string(self):
        """Test creating ExecutionMode from string."""
        assert ExecutionMode("auto") == ExecutionMode.AUTO
        assert ExecutionMode("delegated") == ExecutionMode.DELEGATED
        assert ExecutionMode("sequential") == ExecutionMode.SEQUENTIAL

    def test_execution_mode_invalid_value(self):
        """Test ExecutionMode with invalid value."""
        with pytest.raises(ValueError, match="invalid_mode"):
            ExecutionMode("invalid_mode")

    def test_execution_mode_membership(self):
        """Test membership checking."""
        assert ExecutionMode.AUTO in ExecutionMode
        assert ExecutionMode.HANDOFF in ExecutionMode

    def test_execution_mode_iteration(self):
        """Test iterating over ExecutionMode."""
        modes = list(ExecutionMode)
        assert len(modes) == 7
        assert ExecutionMode.AUTO in modes
        assert ExecutionMode.GROUP_CHAT in modes


class TestTaskStatus:
    """Test suite for TaskStatus enum."""

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_from_string(self):
        """Test creating TaskStatus from string."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("completed") == TaskStatus.COMPLETED

    def test_task_status_comparison(self):
        """Test TaskStatus comparison."""
        assert TaskStatus.PENDING != TaskStatus.COMPLETED
        assert TaskStatus.FAILED == TaskStatus.FAILED

    def test_task_status_terminal_states(self):
        """Test identification of terminal states."""
        terminal_states = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

        assert TaskStatus.COMPLETED in terminal_states
        assert TaskStatus.FAILED in terminal_states
        assert TaskStatus.PENDING not in terminal_states
        assert TaskStatus.IN_PROGRESS not in terminal_states


class TestAgentRole:
    """Test suite for AgentRole enum."""

    def test_agent_role_values(self):
        """Test AgentRole enum values."""
        assert AgentRole.RESEARCHER.value == "researcher"
        assert AgentRole.ANALYST.value == "analyst"
        assert AgentRole.WRITER.value == "writer"
        assert AgentRole.REVIEWER.value == "reviewer"
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.PLANNER.value == "planner"

    def test_agent_role_from_string(self):
        """Test creating AgentRole from string."""
        assert AgentRole("researcher") == AgentRole.RESEARCHER
        assert AgentRole("coder") == AgentRole.CODER

    def test_agent_role_count(self):
        """Test number of defined agent roles."""
        roles = list(AgentRole)
        assert len(roles) == 6


class TestToolResult:
    """Test suite for ToolResult dataclass."""

    def test_tool_result_creation_success(self):
        """Test creating a successful ToolResult."""
        result = ToolResult(
            tool_name="web_search",
            success=True,
            output={"results": ["result1", "result2"]},
            error=None,
            metadata={"duration": 1.5},
        )

        assert result.tool_name == "web_search"
        assert result.success is True
        assert result.output["results"] == ["result1", "result2"]
        assert result.error is None
        assert result.metadata["duration"] == 1.5

    def test_tool_result_creation_failure(self):
        """Test creating a failed ToolResult."""
        result = ToolResult(
            tool_name="api_call",
            success=False,
            output=None,
            error="Connection timeout",
            metadata={},
        )

        assert result.tool_name == "api_call"
        assert result.success is False
        assert result.output is None
        assert result.error == "Connection timeout"

    def test_tool_result_with_empty_metadata(self):
        """Test ToolResult with empty metadata."""
        result = ToolResult(
            tool_name="calculator", success=True, output=42, error=None, metadata={}
        )

        assert result.metadata == {}

    def test_tool_result_with_complex_output(self):
        """Test ToolResult with complex nested output."""
        complex_output = {
            "data": [1, 2, 3],
            "nested": {"key": "value", "list": [{"a": 1}, {"b": 2}]},
        }

        result = ToolResult(
            tool_name="data_processor",
            success=True,
            output=complex_output,
            error=None,
            metadata={},
        )

        assert result.output["nested"]["list"][0]["a"] == 1


class TestTaskResult:
    """Test suite for TaskResult dataclass."""

    def test_task_result_creation(self):
        """Test creating a TaskResult."""
        result = TaskResult(
            task_id="task_123",
            status=TaskStatus.COMPLETED,
            result="Task completed successfully",
            agent_used="researcher",
            execution_time=5.2,
            metadata={"quality_score": 0.9},
        )

        assert result.task_id == "task_123"
        assert result.status == TaskStatus.COMPLETED
        assert result.result == "Task completed successfully"
        assert result.agent_used == "researcher"
        assert result.execution_time == 5.2
        assert result.metadata["quality_score"] == 0.9

    def test_task_result_with_failed_status(self):
        """Test TaskResult with failed status."""
        result = TaskResult(
            task_id="task_456",
            status=TaskStatus.FAILED,
            result=None,
            agent_used="coder",
            execution_time=2.1,
            metadata={"error": "Syntax error"},
        )

        assert result.status == TaskStatus.FAILED
        assert result.result is None
        assert result.metadata["error"] == "Syntax error"

    def test_task_result_with_tools_used(self):
        """Test TaskResult with tools_used field (if exists)."""
        tool_results = [
            ToolResult("web_search", True, {"results": []}, None, {}),
            ToolResult("calculator", True, 42, None, {}),
        ]

        result = TaskResult(
            task_id="task_789",
            status=TaskStatus.COMPLETED,
            result="Analysis done",
            agent_used="analyst",
            execution_time=3.5,
            metadata={"tools_used": [t.tool_name for t in tool_results]},
        )

        assert "web_search" in result.metadata["tools_used"]
        assert "calculator" in result.metadata["tools_used"]


class TestAgentMessage:
    """Test suite for AgentMessage dataclass."""

    def test_agent_message_creation(self):
        """Test creating an AgentMessage."""
        message = AgentMessage(
            role="user",
            content="Please analyze this data",
            agent_name=None,
            timestamp=datetime.now(),
            metadata={},
        )

        assert message.role == "user"
        assert message.content == "Please analyze this data"
        assert message.agent_name is None
        assert isinstance(message.timestamp, datetime)

    def test_agent_message_from_agent(self):
        """Test AgentMessage from an agent."""
        message = AgentMessage(
            role="assistant",
            content="Analysis complete",
            agent_name="analyst",
            timestamp=datetime.now(),
            metadata={"confidence": 0.95},
        )

        assert message.role == "assistant"
        assert message.agent_name == "analyst"
        assert message.metadata["confidence"] == 0.95

    def test_agent_message_with_tool_calls(self):
        """Test AgentMessage with tool calls metadata."""
        message = AgentMessage(
            role="assistant",
            content="Searching web...",
            agent_name="researcher",
            timestamp=datetime.now(),
            metadata={
                "tool_calls": [
                    {"tool": "web_search", "query": "AI agents"},
                ]
            },
        )

        assert len(message.metadata["tool_calls"]) == 1
        assert message.metadata["tool_calls"][0]["tool"] == "web_search"

    def test_agent_message_timestamp_ordering(self):
        """Test ordering messages by timestamp."""
        msg1 = AgentMessage("user", "First", None, datetime(2025, 1, 1, 10, 0), {})
        msg2 = AgentMessage("assistant", "Second", "agent1", datetime(2025, 1, 1, 10, 1), {})

        messages = sorted([msg2, msg1], key=lambda m: m.timestamp or datetime.min)

        assert messages[0] == msg1
        assert messages[1] == msg2


class TestWorkflowState:
    """Test suite for WorkflowState dataclass."""

    def test_workflow_state_creation(self):
        """Test creating a WorkflowState."""
        state = WorkflowState(
            task="Analyze market trends",
            execution_mode=ExecutionMode.SEQUENTIAL,
            current_agent="analyst",
            iteration=2,
            status=TaskStatus.IN_PROGRESS,
            results=[],
            metadata={},
        )

        assert state.task == "Analyze market trends"
        assert state.execution_mode == ExecutionMode.SEQUENTIAL
        assert state.current_agent == "analyst"
        assert state.iteration == 2
        assert state.status == TaskStatus.IN_PROGRESS

    def test_workflow_state_with_results(self):
        """Test WorkflowState with accumulated results."""
        results = [
            TaskResult("sub1", TaskStatus.COMPLETED, "Result 1", "agent1", 1.0, {}),
            TaskResult("sub2", TaskStatus.COMPLETED, "Result 2", "agent2", 2.0, {}),
        ]

        state = WorkflowState(
            task="Complex task",
            execution_mode=ExecutionMode.PARALLEL,
            current_agent=None,
            iteration=1,
            status=TaskStatus.COMPLETED,
            results=results,
            metadata={"total_time": 3.0},
        )

        assert len(state.results) == 2
        assert state.metadata["total_time"] == 3.0

    def test_workflow_state_mode_transition(self):
        """Test workflow state during mode transition."""
        state = WorkflowState(
            task="Task requiring handoff",
            execution_mode=ExecutionMode.HANDOFF,
            current_agent="researcher",
            iteration=3,
            status=TaskStatus.IN_PROGRESS,
            results=[],
            metadata={"handoff_target": "analyst"},
        )

        # Simulate handoff
        state.current_agent = state.metadata["handoff_target"]

        assert state.current_agent == "analyst"
        assert state.execution_mode == ExecutionMode.HANDOFF

    def test_workflow_state_with_history(self):
        """Test WorkflowState with conversation history."""
        messages = [
            AgentMessage("user", "Task", None, datetime.now(), {}),
            AgentMessage("assistant", "Working...", "agent1", datetime.now(), {}),
        ]

        state = WorkflowState(
            task="Task",
            execution_mode=ExecutionMode.AUTO,
            current_agent="agent1",
            iteration=1,
            status=TaskStatus.IN_PROGRESS,
            results=[],
            metadata={"history": messages},
        )

        assert len(state.metadata["history"]) == 2


class TestTypeConversions:
    """Test type conversions and validations."""

    def test_execution_mode_to_string(self):
        """Test converting ExecutionMode to string."""
        mode = ExecutionMode.DELEGATED
        assert str(mode.value) == "delegated"

    def test_task_status_serialization(self):
        """Test TaskStatus serialization."""
        status = TaskStatus.COMPLETED
        serialized = {"status": status.value}

        assert serialized["status"] == "completed"

    def test_tool_result_to_dict(self):
        """Test converting ToolResult to dictionary."""
        result = ToolResult("tool1", True, {"data": 123}, None, {})

        # If dataclass, use asdict
        from dataclasses import asdict

        result_dict = asdict(result)

        assert result_dict["tool_name"] == "tool1"
        assert result_dict["success"] is True

    def test_task_result_json_serializable(self):
        """Test TaskResult JSON serialization."""
        import json

        result = TaskResult(
            task_id="task_1",
            status=TaskStatus.COMPLETED,
            result="Done",
            agent_used="agent1",
            execution_time=1.0,
            metadata={},
        )

        # Convert enum to value for JSON
        result_dict = {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "agent_used": result.agent_used,
            "execution_time": result.execution_time,
            "metadata": result.metadata,
        }

        json_str = json.dumps(result_dict)
        assert "completed" in json_str


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_tool_result_with_none_output_and_error(self):
        """Test ToolResult with both None output and error."""
        result = ToolResult("tool", True, None, None, {})

        assert result.output is None
        assert result.error is None

    def test_task_result_with_zero_execution_time(self):
        """Test TaskResult with zero execution time."""
        result = TaskResult("task", TaskStatus.COMPLETED, "Fast", "agent", 0.0, {})

        assert result.execution_time == 0.0

    def test_workflow_state_with_high_iteration_count(self):
        """Test WorkflowState with high iteration count."""
        state = WorkflowState(
            task="Long task",
            execution_mode=ExecutionMode.SEQUENTIAL,
            current_agent="agent1",
            iteration=999,
            status=TaskStatus.IN_PROGRESS,
            results=[],
            metadata={},
        )

        assert state.iteration == 999

    def test_agent_message_with_empty_content(self):
        """Test AgentMessage with empty content."""
        message = AgentMessage("user", "", None, datetime.now(), {})

        assert message.content == ""

    def test_metadata_with_special_types(self):
        """Test metadata containing special types."""
        metadata = {
            "datetime": datetime.now(),
            "tuple": (1, 2, 3),
            "set": {1, 2, 3},
            "nested_dict": {"a": {"b": {"c": 123}}},
        }

        result = TaskResult("task", TaskStatus.COMPLETED, "Done", "agent", 1.0, metadata)

        assert isinstance(result.metadata["datetime"], datetime)
        assert result.metadata["tuple"] == (1, 2, 3)
