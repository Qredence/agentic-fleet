"""Interactive console helpers for the AgenticFleet CLI."""

import itertools
import threading
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.text import Text


@dataclass
class AgentMessage:
    agent_name: str
    content: str
    mode: str = "response"


@dataclass
class FinalRenderData:
    sections: list[tuple[str, list[str]]] = field(default_factory=list)
    raw_text: str | None = None


class ConsoleUI:
    """Rich-powered console presentation for the REPL."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console(highlight=False)
        self._divider = "_" * 72
        self.reset_run()

        history_path = Path.home() / ".agenticfleet_history"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self._prompt_style = Style.from_dict({"prompt": "bold"})
        self.session: PromptSession = PromptSession(
            history=FileHistory(str(history_path)),
            style=self._prompt_style,
            enable_history_search=True,
        )

    def reset_run(self) -> None:
        self.step_counter = 1

    def show_header(self) -> None:
        self.console.print(Text("AgenticFleet", style="bold"))
        self.console.print(Text("Multi-Agent Orchestration • Magentic Fleet", style="dim"))
        self.console.print(Text(self._divider, style="dim"))
        self.console.print()

    def show_instructions(self) -> None:
        self._print_section(
            "How to Interact",
            [
                "  Type your task and press Enter",
                "  Commands: 'checkpoints' | 'resume <id>' | 'quit'",
            ],
            pre_blank=False,
        )

    async def prompt_async(self, label: str = "Task") -> str:
        with patch_stdout():
            text = await self.session.prompt_async(HTML(f"<prompt>➤ {label.lower()} › </prompt>"))
        return text.strip()

    @contextmanager
    def loading(self, message: str) -> Iterator[None]:
        """Display a shimmer animation while awaiting a result."""

        stop_event = threading.Event()
        spinner_cycle = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])

        def run_animation() -> None:
            with Live(console=self.console, refresh_per_second=8, transient=True) as live:
                while not stop_event.is_set():
                    shimmer = Text(f"{next(spinner_cycle)} {message}", style="bold")
                    live.update(Align.center(shimmer))
                    time.sleep(0.15)

        thread = threading.Thread(target=run_animation, daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop_event.set()
            thread.join(timeout=1)

    def log_task(self, task: str) -> None:
        self.reset_run()
        self._print_section("Task", [task], pre_blank=False)

    def log_plan(self, facts: str | Iterable[str] | None, plan: str | Iterable[str] | None) -> None:
        facts_lines = [line for line in self._format_lines(facts) if line != "(none)"]
        plan_lines = [line for line in self._format_lines(plan) if line != "(none)"]
        body: list[str] = []
        if facts_lines:
            body.append("Facts:")
            body.extend([f"  - {line}" for line in facts_lines])
        if plan_lines:
            body.append("Plan:")
            body.extend([f"  {idx + 1}. {line}" for idx, line in enumerate(plan_lines)])
        if not body:
            body = ["  (none)"]
        self._print_section(f"Plan · Iteration {self.step_counter}", body)
        self.step_counter += 1

    def log_progress(self, status: str, next_speaker: str, instruction: str | None = None) -> None:
        lines = [
            f"Status      : {status}",
            f"Next speaker: {next_speaker}",
        ]
        if instruction:
            instr_lines = self._format_lines(instruction)
            lines.append("Instruction :")
            lines.extend([f"  {line}" for line in instr_lines])
        self._print_section("Progress", lines)

    def log_agent_message(self, message: AgentMessage) -> None:
        lines = [line for line in message.content.strip().splitlines() if line.strip()]
        if not lines:
            return
        self._print_section(f"Agent · {message.agent_name}", [f"  {line}" for line in lines])

    def log_notice(self, text: str, *, style: str = "blue") -> None:
        self._print_section("Notice", [f"  {text}"])

    def log_final(self, result: FinalRenderData | str | None) -> None:
        if isinstance(result, FinalRenderData):
            sections = result.sections or [("Result", ["(none)"])]
            raw_output = result.raw_text or ""
        else:
            normalized = (result or "") if result else ""
            lines = [line.strip() for line in normalized.splitlines() if line.strip()]
            sections = [("Result", lines or ["(none)"])]
            raw_output = normalized

        for index, (title, lines) in enumerate(sections):
            pretty = [f"  {line}" for line in lines] if lines else ["  (none)"]
            self._print_section(title, pretty, pre_blank=index != 0)

        if raw_output and raw_output.strip():
            self.console.print(Text("Raw Output", style="bold"))
            self.console.print(Text(self._divider, style="dim"))
            self.console.print(raw_output)
            self.console.print()

    @staticmethod
    def _format_lines(value: str | Iterable[str | dict[str, Any]] | None) -> list[str]:
        if value is None:
            return ["(none)"]

        if isinstance(value, str):
            normalized = value.replace("\\n", "\n")
            stripped = [v.strip().strip("'\"") for v in normalized.splitlines() if v.strip()]
            return stripped or ["(none)"]

        lines: list[str] = []
        for item in value:
            if isinstance(item, dict):
                for key, val in item.items():
                    lines.append(f"{key}: {val}")
            else:
                text = str(item).strip().strip("'\"")
                text = text.replace("\\n", "\n")
                if text:
                    lines.append(text)

        return lines or ["(none)"]

    def _print_section(self, title: str, lines: Iterable[str], *, pre_blank: bool = True) -> None:
        if pre_blank:
            self.console.print()
        self.console.print(Text(title, style="bold"))
        self.console.print(Text(self._divider, style="dim"))
        for line in lines:
            self.console.print(line)
        self.console.print()
