from typing import ClassVar

from agentic_fleet.dspy_modules.reasoner import DSPyReasoner


def test_supervisor_uses_enhanced_signature_by_default():
    """Verify that DSPyReasoner uses EnhancedTaskRouting by default."""
    supervisor = DSPyReasoner()
    sig = supervisor.router.predict.signature
    assert "tool_plan" in sig.fields
    assert "latency_budget" in sig.fields
    assert "handoff_strategy" in sig.fields


def test_supervisor_enhanced_routing_outputs():
    """Verify that route_task returns enhanced fields."""
    supervisor = DSPyReasoner(use_enhanced_signatures=True)

    class MockEnhancedPrediction:
        assigned_to: ClassVar[list[str]] = ["Researcher"]
        execution_mode = "delegated"
        subtasks: ClassVar[list[str]] = ["Research task"]
        tool_plan: ClassVar[list[str]] = ["TavilySearchTool"]
        tool_goals = "Find information"
        latency_budget = "low"
        handoff_strategy = "None"
        workflow_gates = "None"
        reasoning = "Test reasoning"

    supervisor.router = lambda **kwargs: MockEnhancedPrediction()

    # Use a complex task that won't trigger simple task detection
    result = supervisor.route_task(
        task="Research the latest AI news and analyze trends",
        team={"Researcher": "Search web"},
        context="Context",
    )

    assert result["tool_plan"] == ["TavilySearchTool"]
    assert result["tool_requirements"] == ["TavilySearchTool"]
    assert result["latency_budget"] == "low"
    assert result["tool_goals"] == "Find information"


def test_supervisor_legacy_fallback():
    """Verify that reasoner falls back to TaskRouting when flag is False."""
    supervisor = DSPyReasoner(use_enhanced_signatures=False)
    sig = supervisor.router.predict.signature

    assert "tool_plan" not in sig.fields
    assert "tool_requirements" in sig.fields

    class MockLegacyPrediction:
        assigned_to: ClassVar[list[str]] = ["Agent1"]
        mode = "delegated"
        subtasks: ClassVar[list[str]] = ["Task1"]
        tool_requirements: ClassVar[list[str]] = ["Tool1"]
        reasoning = "Reason"

    supervisor.router = lambda **kwargs: MockLegacyPrediction()

    result = supervisor.route_task("Task", {"Agent": "Desc"})
    assert "tool_requirements" in result
    assert "tool_plan" not in result
