"""Pytest configuration and fixtures."""

import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import dspy
import pytest

# Add project root to Python path so tests can import from src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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
        self.chat_client = chat_client

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
    def __init__(self, data=None, source_executor_id=None):
        self.data = data or {}
        self.source_executor_id = source_executor_id


class WorkflowContext:  # pragma: no cover - stub
    def __init__(self):
        self.data = {}


class Executor:  # pragma: no cover - stub
    def __init__(self, id: str, *args, **kwargs):  # noqa: A002  # matches framework API
        self.id = id


def handler(*args, **kwargs):  # pragma: no cover - stub
    """Decorator stub for executor handlers."""

    def decorator(func):
        return func

    return decorator


class WorkflowBuilder:  # pragma: no cover - stub
    def __init__(self):
        self._executors = {}
        self._edges = []
        self._start_executor = None

    def set_start_executor(self, executor):
        self._start_executor = executor
        return self

    def add_edge(self, from_executor, to_executor):
        self._edges.append((from_executor, to_executor))
        return self

    def build(self):
        class BuiltWorkflow:  # pragma: no cover - stub
            def as_agent(self):
                class WorkflowAgent:  # pragma: no cover - stub
                    async def run(self, task: str):
                        return {"result": f"executed:{task}", "metadata": {}}

                    async def run_stream(self, task: str):
                        if False:
                            yield None

                return WorkflowAgent()

        return BuiltWorkflow()


class WorkflowAgent:  # pragma: no cover - stub
    async def run(self, task: str):
        return {"result": f"executed:{task}", "metadata": {}}

    async def run_stream(self, task: str):
        if False:
            yield None


class AgentRunResponse:  # pragma: no cover - stub
    def __init__(
        self,
        *,
        content: str | None = None,
        messages: list[Any] | None = None,
        role: str | None = None,
        additional_properties: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ):
        self.messages = list(messages) if messages is not None else []
        self.content = content or (self.messages[-1].text if self.messages else "")
        self.role = role or (self.messages[-1].role if self.messages else None)
        self.additional_properties = additional_properties or kwargs.get("metadata", {}) or {}
        self.metadata = metadata or self.additional_properties.get("metadata", {})

    def get_outputs(self) -> list[Any]:
        return self.messages


agent_framework.ToolProtocol = ToolProtocol
agent_framework.HostedCodeInterpreterTool = HostedCodeInterpreterTool
agent_framework.ChatAgent = ChatAgent
agent_framework.ChatMessage = ChatMessage
agent_framework.Role = Role
agent_framework.MagenticAgentMessageEvent = MagenticAgentMessageEvent
agent_framework.MagenticBuilder = MagenticBuilder
agent_framework.WorkflowOutputEvent = WorkflowOutputEvent
agent_framework.WorkflowContext = WorkflowContext
agent_framework.Executor = Executor
agent_framework.handler = handler
agent_framework.WorkflowBuilder = WorkflowBuilder
agent_framework.WorkflowAgent = WorkflowAgent
agent_framework.AgentRunResponse = AgentRunResponse

# Ensure agent_framework.openai submodule exists with OpenAIChatClient stub.
if "agent_framework.openai" not in sys.modules:
    agent_framework_openai = types.ModuleType("agent_framework.openai")
    sys.modules["agent_framework.openai"] = agent_framework_openai
else:
    agent_framework_openai = sys.modules["agent_framework.openai"]


class OpenAIChatClient:  # pragma: no cover - stub
    def __init__(self, *args, **kwargs):
        pass


class OpenAIResponsesClient:  # pragma: no cover - stub
    def __init__(self, *args, **kwargs):
        self.api_key = kwargs.get("api_key")
        self.model_id = kwargs.get("model_id")
        self.extra_body = kwargs.get("extra_body", {})


agent_framework_openai.OpenAIChatClient = OpenAIChatClient
agent_framework_openai.OpenAIResponsesClient = OpenAIResponsesClient

# Ensure agent_framework.exceptions submodule exists with ToolException stubs.
if "agent_framework.exceptions" not in sys.modules:
    agent_framework_exceptions = types.ModuleType("agent_framework.exceptions")
    sys.modules["agent_framework.exceptions"] = agent_framework_exceptions
else:
    agent_framework_exceptions = sys.modules["agent_framework.exceptions"]


class AgentFrameworkException(Exception):  # pragma: no cover - stub  # noqa: N818
    pass


class ToolException(AgentFrameworkException):  # pragma: no cover - stub
    pass


class ToolExecutionError(AgentFrameworkException):  # pragma: no cover - stub
    pass


agent_framework_exceptions.AgentFrameworkException = AgentFrameworkException
agent_framework_exceptions.ToolException = ToolException
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
            if name == "HandoffQualityAssessment":
                return SimpleNamespace(
                    handoff_quality_score="5",
                    context_completeness="yes",
                    success_factors="stubbed",
                    improvement_areas="none",
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
            if name == "QualityAssessment" or name == "JudgeEvaluation":
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
