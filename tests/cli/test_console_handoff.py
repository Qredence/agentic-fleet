"""CLI smoke tests for the handoff command.

Uses Typer's CliRunner and monkeypatch to avoid heavy initialization.
"""

from __future__ import annotations

# Provide minimal stubs for optional third-party deps before importing console
import sys
import types

from typer import Typer
from typer.testing import CliRunner

agent_framework = types.ModuleType("agent_framework")


class _ToolProtocol:  # minimal base
    pass


class _HostedCodeInterpreterTool:
    async def run(self, **kwargs):
        return ""


class _ChatAgent:
    pass


class _MsgEvt:
    pass


class _Builder:
    pass


class _WFEvent:
    pass


agent_framework.ToolProtocol = _ToolProtocol
agent_framework.HostedCodeInterpreterTool = _HostedCodeInterpreterTool
agent_framework.ChatAgent = _ChatAgent
agent_framework.MagenticAgentMessageEvent = _MsgEvt
agent_framework.MagenticBuilder = _Builder
agent_framework.WorkflowOutputEvent = _WFEvent

agent_framework_openai = types.ModuleType("agent_framework.openai")


class _OpenAIChatClient:
    pass


agent_framework_openai.OpenAIChatClient = _OpenAIChatClient

sys.modules.setdefault("agent_framework", agent_framework)
sys.modules.setdefault("agent_framework.openai", agent_framework_openai)

# Stub tavily client dependency
tavily_mod = types.ModuleType("tavily")


class _TavilyClient:
    def __init__(self, *args, **kwargs):
        pass

    def search(self, *args, **kwargs):
        return {"results": [], "answer": ""}


tavily_mod.TavilyClient = _TavilyClient
sys.modules.setdefault("tavily", tavily_mod)


def _import_console_module():
    from agentic_fleet import console as console_module

    return console_module


console = _import_console_module()


def _build_stub_workflow():
    class _StubHandoffManager:
        pass

    class _StubWorkflow:
        def __init__(self):
            self.enable_handoffs = True
            self.handoff_manager = _StubHandoffManager()
            self.agents = {"Researcher": object(), "Analyst": object()}

    return _StubWorkflow()


def test_handoff_command_no_interactive(monkeypatch):
    runner = CliRunner()

    async def fake_init(
        self,
        compile_dspy: bool = True,
        model: str | None = None,
        max_rounds: int = 15,
        enable_handoffs: bool | None = None,
    ):  # type: ignore[no-redef]
        # Attach stub workflow to the runner
        self.workflow = _build_stub_workflow()
        return self.workflow

    # Monkeypatch the async initializer
    monkeypatch.setattr(console.WorkflowRunner, "initialize_workflow", fake_init, raising=True)

    # Build a minimal Typer app containing only the handoff command to avoid
    # validating unrelated options from other commands in this environment.
    local_app = Typer(add_completion=False, no_args_is_help=False)
    local_app.command()(console.handoff)

    # Invoke handoff command in non-interactive mode
    result = runner.invoke(local_app, [], input="exit\n")  # type: ignore[arg-type]

    assert result.exit_code == 0, result.output
