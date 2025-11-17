from __future__ import annotations

from agentic_fleet.dspy_modules.workflow_signatures import EnhancedTaskRouting


def test_enhanced_routing_signature_fields():
    # Ensure signature exposes our efficiency-related outputs for tool-aware ReAct
    sig = EnhancedTaskRouting
    sig_repr = str(sig)
    # Inputs exist
    for name in [
        "task",
        "team_capabilities",
        "available_tools",
        "current_context",
        "handoff_history",
        "workflow_state",
    ]:
        assert name in sig_repr
    # Outputs include extended fields
    for name in ["tool_plan", "tool_goals", "latency_budget"]:
        assert name in sig_repr
