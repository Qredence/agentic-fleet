"""
Tests for handoff workflow functionality.

Tests the HandoffManager, HandoffContext, and handoff-enabled
sequential execution.
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
class ToolProtocol:  # pragma: no cover - stub
    async def run(self, *args, **kwargs):
        raise NotImplementedError


class HostedCodeInterpreterTool(ToolProtocol):  # pragma: no cover - stub
    async def run(self, code: str, **kwargs):
        return f"executed:{code}"


class ChatAgent:  # pragma: no cover - stub
    def __init__(self, name, description="", instructions="", chat_client=None, tools=None):
        self.name = name
        self.description = description or name
        tool_list = tools if isinstance(tools, list) else ([tools] if tools else [])
        self.chat_options = SimpleNamespace(tools=tool_list)

    async def run(self, prompt: str):
        return f"{self.name}:{prompt}"


class ChatMessage:  # pragma: no cover - stub
    def __init__(self, role=None, text: str = "", content: str | None = None, **_):
        self.role = role
        self.text = text or (content or "")
        self.content = content or self.text


class Role:  # pragma: no cover - stub
    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class MagenticAgentMessageEvent:  # pragma: no cover - stub
    def __init__(self, agent_id=None, message=None):
        self.agent_id = agent_id
        self.message = message


class MagenticBuilder:  # pragma: no cover - stub
    pass


class WorkflowOutputEvent:  # pragma: no cover - stub
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


class OpenAIChatClient:  # pragma: no cover - stub
    def __init__(self, *args, **kwargs):
        pass


agent_framework_openai.OpenAIChatClient = OpenAIChatClient

# Ensure agent_framework.exceptions submodule exists with ToolException stubs.
if "agent_framework.exceptions" not in sys.modules:
    agent_framework_exceptions = types.ModuleType("agent_framework.exceptions")
    sys.modules["agent_framework.exceptions"] = agent_framework_exceptions
else:
    agent_framework_exceptions = sys.modules["agent_framework.exceptions"]


class AgentFrameworkException(Exception):  # pragma: no cover - stub  # noqa: N818
    pass


class ToolError(AgentFrameworkException):  # pragma: no cover - stub
    pass


class ToolExecutionError(AgentFrameworkException):  # pragma: no cover - stub
    pass


agent_framework_exceptions.AgentFrameworkException = AgentFrameworkException
agent_framework_exceptions.ToolException = ToolError
agent_framework_exceptions.ToolExecutionException = ToolExecutionError

# Provide tavily stub.
if "tavily" not in sys.modules:
    tavily_mod = types.ModuleType("tavily")

    class TavilyClient:  # pragma: no cover - stub
        def __init__(self, *args, **kwargs):
            pass

        def search(self, *args, **kwargs):
            return {"results": [], "answer": ""}

    tavily_mod.TavilyClient = TavilyClient  # type: ignore[attr-defined]
    sys.modules["tavily"] = tavily_mod


def _import_handoff_modules():
    from agentic_fleet.dspy_modules.supervisor import DSPySupervisor
    from agentic_fleet.workflows.handoff_manager import HandoffContext, HandoffManager
    from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow, WorkflowConfig

    return DSPySupervisor, HandoffContext, HandoffManager, SupervisorWorkflow, WorkflowConfig


(
    DSPySupervisor,
    HandoffContext,
    HandoffManager,
    SupervisorWorkflow,
    WorkflowConfig,
) = _import_handoff_modules()


@pytest.fixture(autouse=True)
def stub_agents(monkeypatch):
    """Avoid constructing real agent-framework objects during tests."""

    class DummyAgent:
        def __init__(self, name: str):
            self.name = name
            self.description = f"{name} stub"
            self.chat_options = SimpleNamespace(tools=[])

        async def run(self, payload: str):
            return f"{self.name}:{payload}"

    class DummyWorkflow:
        async def run(self, task: str):
            return {"result": f"completed:{task}", "metadata": {}}

        async def run_stream(self, task: str):
            if False:
                yield None

    def fake_create_agents(self):
        return {name: DummyAgent(name) for name in ("Researcher", "Analyst", "Writer", "Reviewer")}

    def fake_build_workflow(self):
        return DummyWorkflow()

    monkeypatch.setattr(
        SupervisorWorkflow,
        "_create_agents",
        fake_create_agents,
        raising=True,
    )
    monkeypatch.setattr(
        SupervisorWorkflow,
        "_build_workflow",
        fake_build_workflow,
        raising=True,
    )


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
    supervisor = DSPySupervisor()
    manager = HandoffManager(supervisor)

    assert manager.supervisor == supervisor
    assert len(manager.handoff_history) == 0
    assert manager.handoff_decision_module is not None
    assert manager.handoff_protocol_module is not None


@pytest.mark.asyncio
async def test_evaluate_handoff_no_agents():
    """Test handoff evaluation with no available agents."""
    supervisor = DSPySupervisor()
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
    supervisor = DSPySupervisor()
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
    supervisor = DSPySupervisor()
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
async def test_workflow_handoffs_enabled_by_default():
    """Handoffs are enabled by default in the core app."""
    workflow = SupervisorWorkflow(WorkflowConfig(compile_dspy=False), None)
    await workflow.initialize(compile_dspy=False)

    # Handoffs should be enabled by default
    assert workflow.enable_handoffs is True
    assert workflow.handoff_manager is not None


@pytest.mark.asyncio
async def test_workflow_handoffs_can_be_disabled_via_config():
    """WorkflowConfig flag should disable handoffs when requested."""
    workflow = SupervisorWorkflow(WorkflowConfig(compile_dspy=False, enable_handoffs=False), None)
    await workflow.initialize(compile_dspy=False)

    assert workflow.enable_handoffs is False
    # Manager still constructed but workflow respects toggle
    assert workflow.handoff_manager is not None


@pytest.mark.asyncio
async def test_workflow_with_handoffs_enabled():
    """Test workflow with handoffs enabled."""
    workflow = SupervisorWorkflow(WorkflowConfig(compile_dspy=False), None)
    await workflow.initialize(compile_dspy=False)

    # Enable handoffs
    workflow.enable_handoffs = True

    assert workflow.handoff_manager is not None
    assert workflow.enable_handoffs is True


@pytest.mark.asyncio
async def test_handoff_history_in_execution():
    """Test that handoff history is tracked in execution."""
    workflow = SupervisorWorkflow(WorkflowConfig(compile_dspy=False), None)
    await workflow.initialize(compile_dspy=False)
    workflow.enable_handoffs = True

    # Mock a handoff
    if workflow.handoff_manager:
        workflow.handoff_manager.handoff_history.append(
            HandoffContext(
                from_agent="Researcher",
                to_agent="Analyst",
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

    # Initialize execution
    workflow.current_execution = {"task": "test"}

    # Add handoff history
    if workflow.handoff_manager and workflow.handoff_manager.handoff_history:
        workflow.current_execution["handoff_history"] = [
            handoff.to_dict() for handoff in workflow.handoff_manager.handoff_history
        ]

    assert "handoff_history" in workflow.current_execution
    assert len(workflow.current_execution["handoff_history"]) == 1


@pytest.mark.asyncio
async def test_handoff_export():
    """Test exporting handoff history."""
    import os
    import tempfile

    supervisor = DSPySupervisor()
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


@pytest.mark.asyncio
async def test_format_handoff_input():
    """Test formatting handoff input for next agent."""
    workflow = SupervisorWorkflow(None, WorkflowConfig(compile_dspy=False))
    await workflow.initialize(compile_dspy=False)

    handoff = HandoffContext(
        from_agent="Researcher",
        to_agent="Analyst",
        task="Analyze data",
        work_completed="Collected 100 data points",
        artifacts={"data.csv": "sample"},
        remaining_objectives=["Analyze trends"],
        success_criteria=["Analysis complete"],
        tool_requirements=["HostedCodeInterpreterTool"],
        estimated_effort="moderate",
        quality_checklist=["Verify data quality"],
    )

    formatted = workflow._format_handoff_input(handoff)

    assert "HANDOFF FROM Researcher" in formatted
    assert "Work Completed" in formatted
    assert "Your Objectives" in formatted
    assert "Success Criteria" in formatted
    assert "Quality Checklist" in formatted
    assert "Analyze trends" in formatted


@pytest.mark.asyncio
async def test_handoff_manager_clear_history():
    """Test clearing handoff history."""
    supervisor = DSPySupervisor()
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
async def test_extract_artifacts():
    """Test artifact extraction from agent result."""
    workflow = SupervisorWorkflow(None, WorkflowConfig(compile_dspy=False))
    await workflow.initialize(compile_dspy=False)

    result = "This is a test result with some data"
    artifacts = workflow._extract_artifacts(result)

    assert isinstance(artifacts, dict)
    assert "result_summary" in artifacts


@pytest.mark.asyncio
async def test_estimate_remaining_work():
    """Test estimating remaining work."""
    workflow = SupervisorWorkflow(None, WorkflowConfig(compile_dspy=False))
    await workflow.initialize(compile_dspy=False)

    original_task = "Research and analyze market trends"
    work_done = "Completed research phase"

    remaining = workflow._estimate_remaining_work(original_task, work_done)

    assert isinstance(remaining, str)
    assert "Continue working on" in remaining


@pytest.mark.asyncio
async def test_derive_objectives():
    """Test deriving objectives from remaining work."""
    workflow = SupervisorWorkflow(None, WorkflowConfig(compile_dspy=False))
    await workflow.initialize(compile_dspy=False)

    remaining_work = "Analyze data and create visualizations"
    objectives = workflow._derive_objectives(remaining_work)

    assert isinstance(objectives, list)
    assert len(objectives) > 0


# === New tests for compiled supervisor integration and fallback behavior ===


@pytest.mark.asyncio
async def test_handoff_manager_uses_compiled_supervisor_chains():
    """Ensure HandoffManager prefers compiled supervisor handoff chains when provided."""
    supervisor = DSPySupervisor()

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
    assert isinstance(handoff.quality_checklist, list) and len(handoff.quality_checklist) == 2

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
    """When compiled supervisor is unavailable, use base DSPySupervisor chains."""
    supervisor = DSPySupervisor()
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


@pytest.mark.asyncio
async def test_supervisor_workflow_handoff_manager_prefers_compiled_supervisor_when_available(
    monkeypatch,
):
    """SupervisorWorkflow wires HandoffManager with compiled supervisor provider."""
    wf = SupervisorWorkflow(WorkflowConfig(compile_dspy=False))
    await wf.initialize(compile_dspy=False)

    # Create compiled stub and inject into workflow's compiled supervisor slot
    class CompiledSupervisorStub:
        def __init__(self):
            self.calls = {"handoff_decision": 0}

        def handoff_decision(self, **kwargs):
            self.calls["handoff_decision"] += 1
            return SimpleNamespace(
                should_handoff="yes",
                next_agent="Analyst",
                handoff_reason="compiled-from-workflow",
            )

    compiled = CompiledSupervisorStub()
    # Simulate background compilation completion
    wf._compiled_supervisor = compiled

    # HandoffManager should now prefer compiled supervisor via provider
    manager = wf.handoff_manager
    assert manager is not None

    next_agent = await manager.evaluate_handoff(
        current_agent="Researcher",
        work_completed="Data collected",
        remaining_work="Analyze results",
        available_agents={"Analyst": "Data analysis"},
        agent_states={"Analyst": "available"},
    )
    assert next_agent == "Analyst"
    assert compiled.calls["handoff_decision"] == 1


@pytest.mark.asyncio
async def test_import_guard_agent_framework_stubs_present(monkeypatch):
    """Verify SupervisorWorkflow can initialize with agent_framework stubs in tests."""
    # Remove agent_framework from sys.modules to trigger stub path in test fixtures
    import sys as _sys

    _sys.modules.pop("agent_framework", None)
    _sys.modules.pop("agent_framework.openai", None)

    wf = SupervisorWorkflow(WorkflowConfig(compile_dspy=False))
    # initialize relies on test autouse fixtures providing stubs
    await wf.initialize(compile_dspy=False)

    # Basic sanity: handoff manager exists and wiring via provider lambda is set
    assert wf.handoff_manager is not None
    assert callable(getattr(wf.handoff_manager, "_get_compiled_supervisor", None))
