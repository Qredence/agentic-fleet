"""
Tests for handoff workflow functionality.

Tests the HandoffManager and HandoffContext.
"""

import sys
import types
from types import SimpleNamespace

import dspy
import pytest

# Provide lightweight stubs when third-party packages are unavailable.

if "agent_framework" not in sys.modules:
    agent_framework = types.ModuleType("agent_framework")
    agent_framework.__path__ = []  # type: ignore[attr-defined]
    sys.modules["agent_framework"] = agent_framework
else:
    agent_framework = sys.modules["agent_framework"]


# Overwrite attributes so imports see the test stubs regardless of prior state.
class ToolProtocol:
    async def run(self, *args, **kwargs):
        raise NotImplementedError


class HostedCodeInterpreterTool(ToolProtocol):
    async def run(self, code: str, **kwargs):
        return f"executed:{code}"


class ChatAgent:
    def __init__(self, name, description="", instructions="", chat_client=None, tools=None):
        self.name = name
        self.description = description or name
        tool_list = tools if isinstance(tools, list) else ([tools] if tools else [])
        self.chat_options = SimpleNamespace(tools=tool_list)

    async def run(self, prompt: str):
        return f"{self.name}:{prompt}"


class ChatMessage:
    def __init__(self, role=None, text: str = "", content: str | None = None, **_):
        self.role = role
        self.text = text or (content or "")
        self.content = content or self.text


class Role:
    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class MagenticAgentMessageEvent:
    def __init__(self, agent_id=None, message=None):
        self.agent_id = agent_id
        self.message = message


class MagenticBuilder:
    pass


class WorkflowOutputEvent:
    pass


agent_framework.ToolProtocol = ToolProtocol
agent_framework.HostedCodeInterpreterTool = HostedCodeInterpreterTool
agent_framework.ChatAgent = ChatAgent
agent_framework.ChatMessage = ChatMessage
agent_framework.Role = Role
agent_framework.MagenticAgentMessageEvent = MagenticAgentMessageEvent
agent_framework.MagenticBuilder = MagenticBuilder
agent_framework.WorkflowOutputEvent = WorkflowOutputEvent

# Ensure agent_framework.openai submodule exists with OpenAIChatClient stub.
if "agent_framework.openai" not in sys.modules:
    agent_framework_openai = types.ModuleType("agent_framework.openai")
    sys.modules["agent_framework.openai"] = agent_framework_openai
else:
    agent_framework_openai = sys.modules["agent_framework.openai"]


class OpenAIChatClient:
    def __init__(self, *args, **kwargs):
        pass


agent_framework_openai.OpenAIChatClient = OpenAIChatClient

# Ensure agent_framework.exceptions submodule exists with ToolException stubs.
if "agent_framework.exceptions" not in sys.modules:
    agent_framework_exceptions = types.ModuleType("agent_framework.exceptions")
    sys.modules["agent_framework.exceptions"] = agent_framework_exceptions
else:
    agent_framework_exceptions = sys.modules["agent_framework.exceptions"]


class AgentFrameworkError(Exception):  # pragma: no cover - stub
    pass


class ToolError(AgentFrameworkError):  # pragma: no cover - stub
    pass


class ToolExecutionError(AgentFrameworkError):  # pragma: no cover - stub
    pass


agent_framework_exceptions.AgentFrameworkException = AgentFrameworkError
agent_framework_exceptions.ToolException = ToolError
agent_framework_exceptions.ToolExecutionException = ToolExecutionError

# Provide tavily stub.
if "tavily" not in sys.modules:
    tavily_mod = types.ModuleType("tavily")

    class TavilyClient:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, *args, **kwargs):
            return {"results": [], "answer": ""}

    tavily_mod.TavilyClient = TavilyClient  # type: ignore[attr-defined]
    sys.modules["tavily"] = tavily_mod


def _import_handoff_modules():
    from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
    from agentic_fleet.workflows.handoff import HandoffContext, HandoffManager

    return DSPyReasoner, HandoffContext, HandoffManager


(
    DSPyReasoner,
    HandoffContext,
    HandoffManager,
) = _import_handoff_modules()


@pytest.fixture(autouse=True)
def stub_dspy(monkeypatch):
    """Stub DSPy LM and ChainOfThought to avoid network/model constraints during tests."""

    class FakeLM:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(dspy, "LM", lambda *args, **kwargs: FakeLM())

    class DummyChain:
        def __init__(self, signature):
            self.signature = signature

        def __call__(self, **kwargs):
            name = getattr(self.signature, "__name__", "")
            if name == "HandoffDecision":
                return SimpleNamespace(
                    should_handoff="no",
                    next_agent="",
                    handoff_context="",
                    handoff_reason="stubbed",
                )
            if name == "HandoffProtocol":
                return SimpleNamespace(
                    handoff_package="handoff package",
                    quality_checklist="verify outputs",
                    estimated_effort="simple",
                )
            if name == "TaskRouting":
                return SimpleNamespace(
                    assigned_to="Researcher,Analyst",
                    execution_mode="sequential",
                    subtasks="Investigate\nSummarize",
                )
            if name == "TaskAnalysis" or name == "ToolAwareTaskAnalysis":
                return SimpleNamespace(
                    needs_web_search="no",
                    search_query="",
                    complexity="simple",
                    required_capabilities="analysis",
                    tool_requirements="HostedCodeInterpreterTool",
                    estimated_steps="3",
                )
            if name == "ProgressEvaluation":
                return SimpleNamespace(next_action="continue", feedback="proceed")
            if name == "QualityAssessment":
                return SimpleNamespace(
                    quality_score="10",
                    missing_elements="",
                    improvement_suggestions="",
                )
            return SimpleNamespace()

    monkeypatch.setattr(dspy, "ChainOfThought", DummyChain)

    class _Settings:
        def configure(self, **kwargs):
            return None

    monkeypatch.setattr(dspy, "settings", _Settings())


@pytest.mark.asyncio
async def test_handoff_context_creation():
    """Test creating a HandoffContext."""
    context = HandoffContext(
        from_agent="Researcher",
        to_agent="Analyst",
        task="Analyze data",
        work_completed="Gathered 100 data points",
        artifacts={"data.csv": "sample data"},
        remaining_objectives=["Analyze trends", "Create visualizations"],
        success_criteria=["Analysis complete", "Charts created"],
        tool_requirements=["HostedCodeInterpreterTool"],
        estimated_effort="moderate",
        quality_checklist=["Verify data quality", "Check calculations"],
        handoff_reason="Research complete, need analysis",
    )

    assert context.from_agent == "Researcher"
    assert context.to_agent == "Analyst"
    assert len(context.remaining_objectives) == 2
    assert context.estimated_effort == "moderate"


@pytest.mark.asyncio
async def test_handoff_context_serialization():
    """Test HandoffContext serialization and deserialization."""
    original = HandoffContext(
        from_agent="Writer",
        to_agent="Reviewer",
        task="Review document",
        work_completed="Draft created",
        artifacts={},
        remaining_objectives=["Review content"],
        success_criteria=["Approved"],
        tool_requirements=[],
        estimated_effort="simple",
        quality_checklist=["Check grammar"],
    )

    # Convert to dict
    data = original.to_dict()
    assert isinstance(data, dict)
    assert data["from_agent"] == "Writer"

    # Recreate from dict
    restored = HandoffContext.from_dict(data)
    assert restored.from_agent == original.from_agent
    assert restored.to_agent == original.to_agent


@pytest.mark.asyncio
async def test_handoff_manager_initialization():
    """Test HandoffManager initialization."""
    supervisor = DSPyReasoner()
    manager = HandoffManager(supervisor)

    assert manager.supervisor == supervisor
    assert len(manager.handoff_history) == 0
    assert manager.handoff_decision_module is not None
    assert manager.handoff_protocol_module is not None


@pytest.mark.asyncio
async def test_evaluate_handoff_no_agents():
    """Test handoff evaluation with no available agents."""
    supervisor = DSPyReasoner()
    manager = HandoffManager(supervisor)

    result = await manager.evaluate_handoff(
        current_agent="Researcher",
        work_completed="Research done",
        remaining_work="Need analysis",
        available_agents={},
    )

    assert result is None


@pytest.mark.asyncio
async def test_create_handoff_package():
    """Test creating a handoff package."""
    supervisor = DSPyReasoner()
    manager = HandoffManager(supervisor)

    # When DSPy module call fails, should create fallback handoff
    handoff = await manager.create_handoff_package(
        from_agent="Researcher",
        to_agent="Analyst",
        work_completed="Research complete",
        artifacts={"data": "sample"},
        remaining_objectives=["Analyze", "Visualize"],
        task="Research and analyze data",
        handoff_reason="Sequential workflow",
    )

    # Should still create a handoff (fallback)
    assert handoff.from_agent == "Researcher"
    assert handoff.to_agent == "Analyst"
    assert len(handoff.remaining_objectives) == 2
    # Fallback creates handoff but may not add to history if module fails
    assert handoff.estimated_effort in ["simple", "moderate", "complex"]


@pytest.mark.asyncio
async def test_handoff_manager_statistics():
    """Test handoff statistics generation."""
    supervisor = DSPyReasoner()
    manager = HandoffManager(supervisor)

    # Create mock handoffs
    for i in range(3):
        manager.handoff_history.append(
            HandoffContext(
                from_agent="Researcher",
                to_agent="Analyst",
                task=f"Task {i}",
                work_completed=f"Work {i}",
                artifacts={},
                remaining_objectives=[],
                success_criteria=[],
                tool_requirements=[],
                estimated_effort="moderate",
                quality_checklist=[],
            )
        )

    stats = manager.get_handoff_summary()
    assert stats["total_handoffs"] == 3
    assert "handoff_pairs" in stats
    assert "Researcher → Analyst" in stats["handoff_pairs"]


@pytest.mark.asyncio
async def test_handoff_manager_clear_history():
    """Test clearing handoff history."""
    supervisor = DSPyReasoner()
    manager = HandoffManager(supervisor)

    # Add some handoffs
    manager.handoff_history.append(
        HandoffContext(
            from_agent="A",
            to_agent="B",
            task="Test",
            work_completed="Done",
            artifacts={},
            remaining_objectives=[],
            success_criteria=[],
            tool_requirements=[],
            estimated_effort="simple",
            quality_checklist=[],
        )
    )

    assert len(manager.handoff_history) == 1

    manager.clear_history()
    assert len(manager.handoff_history) == 0


@pytest.mark.asyncio
async def test_handoff_export():
    """Test exporting handoff history."""
    import os
    import tempfile

    supervisor = DSPyReasoner()
    manager = HandoffManager(supervisor)

    # Create a handoff
    manager.handoff_history.append(
        HandoffContext(
            from_agent="Researcher",
            to_agent="Analyst",
            task="Test",
            work_completed="Done",
            artifacts={"test": "data"},
            remaining_objectives=["Analyze"],
            success_criteria=["Complete"],
            tool_requirements=[],
            estimated_effort="simple",
            quality_checklist=["Check"],
        )
    )

    # Export to temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = f.name

    try:
        manager.export_history(temp_path)
        assert os.path.exists(temp_path)

        # Verify file content
        import json

        with open(temp_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["from_agent"] == "Researcher"
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


# === New tests for compiled supervisor integration and fallback behavior ===


@pytest.mark.asyncio
async def test_handoff_manager_uses_compiled_supervisor_chains():
    """Ensure HandoffManager prefers compiled supervisor handoff chains when provided."""
    supervisor = DSPyReasoner()

    class CompiledSupervisorStub:
        def __init__(self):
            self.calls = {
                "handoff_decision": 0,
                "handoff_protocol": 0,
                "handoff_quality_assessor": 0,
            }

        def handoff_decision(self, **kwargs):
            self.calls["handoff_decision"] += 1
            return SimpleNamespace(
                should_handoff="yes",
                next_agent="Analyst",
                handoff_reason="compiled",
            )

        def handoff_protocol(self, **kwargs):
            self.calls["handoff_protocol"] += 1
            return SimpleNamespace(
                handoff_package="compiled_package",
                quality_checklist="Item A\nItem B",
                estimated_effort="complex",
            )

        def handoff_quality_assessor(self, **kwargs):
            self.calls["handoff_quality_assessor"] += 1
            return SimpleNamespace(
                handoff_quality_score="9",
                context_completeness="yes",
                success_factors="context clear",
                improvement_areas="none",
            )

    compiled = CompiledSupervisorStub()
    manager = HandoffManager(supervisor, get_compiled_supervisor=lambda: compiled)

    # Evaluate handoff - should use compiled.handoff_decision
    next_agent = await manager.evaluate_handoff(
        current_agent="Researcher",
        work_completed="Research complete",
        remaining_work="Need analysis",
        available_agents={"Analyst": "Data analysis"},
        agent_states={"Analyst": "available"},
    )
    assert next_agent == "Analyst"

    # Create package - should use compiled.handoff_protocol
    handoff = await manager.create_handoff_package(
        from_agent="Researcher",
        to_agent="Analyst",
        work_completed="Findings...",
        artifacts={"report": "ok"},
        remaining_objectives=["Analyze dataset", "Summarize"],
        task="Analyze and summarize",
        handoff_reason="Sequential workflow",
    )
    assert handoff.estimated_effort == "complex"
    assert handoff.metadata.get("protocol_package") == "compiled_package"
    assert isinstance(handoff.quality_checklist, list)
    assert len(handoff.quality_checklist) == 2

    # Assess quality - should use compiled.handoff_quality_assessor
    quality = await manager.assess_handoff_quality(handoff, work_after_handoff="Analysis done")
    assert quality["quality_score"] == 9.0
    assert quality["context_complete"] is True
    assert "context clear" in quality["success_factors"]

    # Ensure compiled chains were used exactly once each
    assert compiled.calls["handoff_decision"] == 1
    assert compiled.calls["handoff_protocol"] == 1
    assert compiled.calls["handoff_quality_assessor"] == 1


@pytest.mark.asyncio
async def test_handoff_manager_uses_base_supervisor_chains_when_compiled_unavailable():
    """When compiled supervisor is unavailable, use base DSPyReasoner chains."""
    supervisor = DSPyReasoner()
    manager = HandoffManager(supervisor, get_compiled_supervisor=lambda: None)

    # Evaluate handoff via base supervisor chain (stubbed DummyChain returns 'no')
    next_agent = await manager.evaluate_handoff(
        current_agent="Researcher",
        work_completed="Research complete",
        remaining_work="Need analysis",
        available_agents={"Analyst": "Data analysis"},
        agent_states={"Analyst": "available"},
    )
    assert next_agent is None  # DummyChain returns should_handoff='no'

    # Create handoff via base supervisor chain (DummyChain -> estimated_effort='simple')
    handoff = await manager.create_handoff_package(
        from_agent="Researcher",
        to_agent="Analyst",
        work_completed="Findings...",
        artifacts={"report": "ok"},
        remaining_objectives=["Analyze dataset"],
        task="Analyze and summarize",
        handoff_reason="Sequential workflow",
    )
    assert handoff.estimated_effort in ("simple", "moderate", "complex")
    # Base chain path should also append to history
    assert len(manager.handoff_history) >= 1

    # Assess quality via base chain. DummyChain does not implement HandoffQualityAssessment,
    # so the manager should return a safe default assessment dict.
    quality = await manager.assess_handoff_quality(handoff, work_after_handoff="Analysis done")
    assert isinstance(quality, dict)
    assert "quality_score" in quality
    assert "context_complete" in quality
