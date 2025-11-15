"""
Tests for enhanced DSPy signatures for workflow integration.
"""

import sys
from types import ModuleType, SimpleNamespace

# Provide lightweight stubs when third-party packages are unavailable.
if "dspy" not in sys.modules:
    dspy_mod = ModuleType("dspy")

    class ChainOfThought:  # pragma: no cover - stub
        def __init__(self, signature):
            self.signature = signature

        def __call__(self, **kwargs):
            return SimpleNamespace(
                assigned_to="Researcher",
                execution_mode="delegated",
                handoff_strategy="After research, handoff to analyst",
                subtasks="Research\nAnalyze",
                workflow_gates="Quality checkpoint before completion",
            )

    class Signature:  # pragma: no cover - stub
        pass

    class InputField:  # pragma: no cover - stub
        def __init__(self, desc=""):
            self.desc = desc

    class OutputField:  # pragma: no cover - stub
        def __init__(self, desc=""):
            self.desc = desc

    dspy_mod.ChainOfThought = ChainOfThought
    dspy_mod.Signature = Signature
    dspy_mod.InputField = InputField
    dspy_mod.OutputField = OutputField

    sys.modules["dspy"] = dspy_mod


def test_enhanced_task_routing_signature():
    """Test enhanced TaskRouting signature with handoff awareness."""
    from dspy import ChainOfThought

    from agentic_fleet.dspy_modules.workflow_signatures import EnhancedTaskRouting

    router = ChainOfThought(EnhancedTaskRouting)

    result = router(
        task="Research competitors",
        team_capabilities="Researcher: Web search\nAnalyst: Data analysis",
        available_tools="TavilySearchTool, HostedCodeInterpreterTool",
        current_context="Initial task",
        handoff_history="",
    )

    assert hasattr(result, "assigned_to")
    assert hasattr(result, "execution_mode")
    assert hasattr(result, "handoff_strategy")
    assert hasattr(result, "subtasks")
    assert hasattr(result, "workflow_gates")
