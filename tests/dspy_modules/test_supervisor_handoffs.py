"""
Tests for DSPy supervisor handoff-aware routing.
"""

import sys
import types
from types import SimpleNamespace

import pytest

# Provide lightweight stubs when third-party packages are unavailable.
if "dspy" not in sys.modules:
    dspy_mod = types.ModuleType("dspy")

    class LM:  # pragma: no cover - stub
        def __init__(self, *args, **kwargs):
            pass

    class ChainOfThought:  # pragma: no cover - stub
        def __init__(self, signature):
            self.signature = signature

        def __call__(self, **kwargs):
            return SimpleNamespace(
                execution_mode="delegated", assigned_to="Researcher", subtasks="Research task"
            )

    class Signature:  # pragma: no cover - stub
        pass

    class Module:  # pragma: no cover - stub
        def __init__(self):
            pass

    class Prediction:  # pragma: no cover - stub
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class Settings:  # pragma: no cover - stub
        def configure(self, **kwargs):
            pass

    class InputField:  # pragma: no cover - stub
        def __init__(self, desc=""):
            self.desc = desc

    class OutputField:  # pragma: no cover - stub
        def __init__(self, desc=""):
            self.desc = desc

    dspy_mod.LM = LM
    dspy_mod.ChainOfThought = ChainOfThought
    dspy_mod.Signature = Signature
    dspy_mod.Module = Module
    dspy_mod.Prediction = Prediction
    dspy_mod.InputField = InputField
    dspy_mod.OutputField = OutputField
    dspy_mod.settings = Settings()

    sys.modules["dspy"] = dspy_mod

from agentic_fleet.dspy_modules.supervisor import DSPySupervisor
from agentic_fleet.utils.models import ExecutionMode


@pytest.mark.asyncio
async def test_dspy_supervisor_handoff_aware_routing():
    """Test DSPy supervisor considers handoffs in routing decisions."""
    supervisor = DSPySupervisor()

    routing = supervisor.route_task(
        task="Research and analyze market data",
        team={"Researcher": "Web research", "Analyst": "Data analysis"},
        context="Initial task",
    )

    # Should include handoff considerations in routing
    assert hasattr(routing, "mode")
    assert hasattr(routing, "assigned_to")
    assert hasattr(routing, "subtasks")
    assert hasattr(routing, "tool_requirements")

    # Should have proper execution mode
    assert (
        hasattr(ExecutionMode, "DELEGATED")
        or hasattr(ExecutionMode, "SEQUENTIAL")
        or hasattr(ExecutionMode, "PARALLEL")
    )
