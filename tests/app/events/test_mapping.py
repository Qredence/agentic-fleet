"""Tests for event mapping logic."""

from agent_framework._types import AgentRunResponse, ChatMessage, Role
from agent_framework._workflows import (
    ExecutorCompletedEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
)

from agentic_fleet.api.events.mapping import classify_event, map_workflow_event
from agentic_fleet.models import EventCategory, StreamEventType
from agentic_fleet.workflows.models import (
    AnalysisMessage,
    AnalysisResult,
    MagenticAgentMessageEvent,
    ReasoningStreamEvent,
)


def test_classify_event():
    """Test event classification logic."""
    # Test orchestrator thought
    cat, hint = classify_event(StreamEventType.ORCHESTRATOR_THOUGHT, kind="routing")
    assert cat == EventCategory.PLANNING
    assert hint.component == "ChatStep"
    assert hint.icon_hint == "routing"

    # Test agent start
    cat, hint = classify_event(StreamEventType.AGENT_START)
    assert cat == EventCategory.STEP
    assert hint.component == "ChatStep"
    assert hint.icon_hint == "agent_start"

    # Test error
    cat, hint = classify_event(StreamEventType.ERROR)
    assert cat == EventCategory.ERROR
    assert hint.component == "ErrorStep"


def test_map_workflow_started():
    """Test mapping WorkflowStartedEvent - should be skipped (returns None)."""
    event = WorkflowStartedEvent(data=None)
    mapped, _ = map_workflow_event(event, "")
    # WorkflowStartedEvent is now filtered out (returns None) because it's not useful UI data
    assert mapped is None


def test_map_agent_message():
    """Test mapping MagenticAgentMessageEvent."""
    msg = ChatMessage(role=Role.ASSISTANT, text="Hello world")
    event = MagenticAgentMessageEvent(agent_id="TestAgent", message=msg)

    mapped, _ = map_workflow_event(event, "")
    assert mapped is not None
    assert not isinstance(mapped, list)
    assert mapped.type == StreamEventType.AGENT_MESSAGE
    assert mapped.message == "Hello world"
    assert mapped.agent_id == "TestAgent"
    assert mapped.category == EventCategory.OUTPUT


def test_map_reasoning_event():
    """Test mapping ReasoningStreamEvent."""
    event = ReasoningStreamEvent(reasoning="Thinking...", agent_id="GPT-5")
    mapped, acc = map_workflow_event(event, "Previous")

    assert mapped is not None
    assert not isinstance(mapped, list)
    assert mapped.type == StreamEventType.REASONING_DELTA
    assert mapped.reasoning == "Thinking..."
    assert acc == "PreviousThinking..."


def test_map_analysis_completion():
    """Test mapping ExecutorCompletedEvent with AnalysisMessage."""
    analysis = AnalysisResult(
        complexity="medium",
        capabilities=["research"],
        tool_requirements=[],
        steps=3,
        search_context="",
        needs_web_search=False,
        search_query="",
    )
    msg = AnalysisMessage(task="test", analysis=analysis)
    # Ensure ExecutorCompletedEvent is instantiated correctly according to framework definition
    # Assuming it accepts executor_id and data as keyword arguments
    event = ExecutorCompletedEvent(executor_id="analysis", data=msg)

    mapped, _ = map_workflow_event(event, "")
    assert mapped is not None
    assert not isinstance(mapped, list)
    assert mapped.type == StreamEventType.ORCHESTRATOR_THOUGHT
    assert mapped.kind == "analysis"
    assert mapped.category == EventCategory.THOUGHT
    assert mapped.data is not None
    assert mapped.data["complexity"] == "medium"


def test_map_workflow_output():
    """Test mapping WorkflowOutputEvent."""
    msg = ChatMessage(role=Role.ASSISTANT, text="Final answer")
    event = WorkflowOutputEvent(data=[msg], source_executor_id="test")

    mapped_events, _ = map_workflow_event(event, "")
    assert isinstance(mapped_events, list)
    assert len(mapped_events) == 2

    # First event should be the agent message
    assert mapped_events[0].type == StreamEventType.AGENT_MESSAGE
    assert mapped_events[0].message == "Final answer"

    # Second event should be response completed
    assert mapped_events[1].type == StreamEventType.RESPONSE_COMPLETED
    assert mapped_events[1].message == "Final answer"


def test_map_workflow_output_agent_run_response():
    """Test mapping WorkflowOutputEvent with AgentRunResponse payload."""
    msg = ChatMessage(role=Role.ASSISTANT, text="Structured answer")
    arr = AgentRunResponse(
        messages=[msg], additional_properties={"structured_output": {"foo": "bar"}}
    )
    event = WorkflowOutputEvent(data=arr, source_executor_id="test")

    mapped_events, _ = map_workflow_event(event, "")
    assert isinstance(mapped_events, list)
    assert len(mapped_events) == 2

    assert mapped_events[0].type == StreamEventType.AGENT_MESSAGE
    assert mapped_events[0].message == "Structured answer"

    assert mapped_events[1].type == StreamEventType.RESPONSE_COMPLETED
    assert mapped_events[1].data == {"structured_output": {"foo": "bar"}}
