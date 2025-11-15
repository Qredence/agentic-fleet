"""
Tests for agent-framework integration with DSPy supervisor.
"""

import sys
import types
from types import SimpleNamespace

import pytest

# Provide lightweight stubs when third-party packages are unavailable.
if "agent_framework" not in sys.modules:
    agent_framework = types.ModuleType("agent_framework")

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
    agent_framework.MagenticAgentMessageEvent = MagenticAgentMessageEvent
    agent_framework.MagenticBuilder = MagenticBuilder
    agent_framework.WorkflowOutputEvent = WorkflowOutputEvent

    agent_framework_openai = types.ModuleType("agent_framework.openai")

    class OpenAIChatClient:  # pragma: no cover - stub
        def __init__(self, *args, **kwargs):
            pass

    agent_framework_openai.OpenAIChatClient = OpenAIChatClient

    sys.modules["agent_framework"] = agent_framework
    sys.modules["agent_framework.openai"] = agent_framework_openai

if "dspy" not in sys.modules:
    dspy_mod = types.ModuleType("dspy")

    class LM:  # pragma: no cover - stub
        def __init__(self, *args, **kwargs):
            pass

    class ChainOfThought:  # pragma: no cover - stub
        def __init__(self, signature):
            self.signature = signature

        def __call__(self, **kwargs):
            return SimpleNamespace()

    class Signature:  # pragma: no cover - stub
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

    class Module:  # pragma: no cover - stub
        def __init__(self):
            pass

    dspy_mod.LM = LM
    dspy_mod.ChainOfThought = ChainOfThought
    dspy_mod.Signature = Signature
    dspy_mod.Module = Module
    dspy_mod.Prediction = Prediction
    dspy_mod.InputField = InputField
    dspy_mod.OutputField = OutputField
    dspy_mod.settings = Settings()

    sys.modules["dspy"] = dspy_mod

# Note: agent_framework_adapter.py was removed as it's not used in production
# from src.workflows.agent_framework_adapter import AgentFrameworkAdapter


@pytest.mark.skip(
    reason="agent_framework_adapter.py was removed - functionality moved to SupervisorWorkflow"
)
@pytest.mark.asyncio
async def test_agent_framework_adapter():
    """Test that adapter handles DSPy and agent-framework integration."""
    pass


@pytest.mark.skip(
    reason="agent_framework_adapter.py was removed - functionality moved to SupervisorWorkflow"
)
@pytest.mark.asyncio
async def test_agent_framework_native_handoffs():
    """Test that workflow uses agent-framework's native handoff mechanisms."""
    pass
