"""Interactive console helpers for the AgenticFleet CLI."""

from __future__ import annotations

import itertools
import threading
import time
from collections.abc import Iterable, Iterator, Sequence
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
    """Represents a message emitted by an agent participant."""

    agent_name: str
    content: str
    mode: str = "response"


@dataclass
class FinalRenderData:
    """Structured payload used when rendering the final answer."""

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
        """Reset counters for the next orchestration run."""

        self.step_counter = 1

    def show_header(self) -> None:
        """Render the CLI header banner."""

        self.console.print(Text("AgenticFleet", style="bold"))
        self.console.print(Text("Multi-Agent Orchestration • Magentic Fleet", style="dim"))
        self.console.print(Text(self._divider, style="dim"))
        self.console.print()

    def show_instructions(self) -> None:
        """Show usage instructions."""

        self._print_section(
            "How to Interact",
            [
                "  Type your task and press Enter",
                "  Commands: 'checkpoints' | 'resume <id>' | 'quit'",
            ],
            pre_blank=False,
        )

    async def prompt_async(self, label: str = "Task") -> str:
        """Prompt the operator for input, preserving Rich output."""

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
        """Record the starting task description."""

        self.reset_run()
        self._print_section("Task", [task], pre_blank=False)

    def log_plan(self, facts: str | Iterable[str] | None, plan: str | Iterable[str] | None) -> None:
        """Render the manager's plan and gathered facts."""

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
        """Render the latest progress ledger line."""

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
        """Render a specialist agent response."""

        lines = [line for line in message.content.strip().splitlines() if line.strip()]
        if not lines:
            return
        self._print_section(f"Agent · {message.agent_name}", [f"  {line}" for line in lines])

    def log_notice(self, text: str, *, style: str = "blue") -> None:
        """Render a notice message."""

        self._print_section("Notice", [f"  {text}"], style=style)

    def log_final(self, result: FinalRenderData | str | Any | None) -> None:
        """Render the final answer payload."""

        sections: list[tuple[str, list[str]]]
        raw_output: str

        if isinstance(result, FinalRenderData):
            sections = result.sections or [("Result", ["(none)"])]
            raw_output = result.raw_text or ""
        elif isinstance(result, str):
            normalized = result or ""
            lines = [line.strip() for line in normalized.splitlines() if line.strip()]
            sections = [("Result", lines or ["(none)"])]
            raw_output = normalized
        elif result is None:
            sections = [("Result", ["(none)"])]
            raw_output = ""
        else:
            message = getattr(result, "message", result)
            sections = []
            raw_output = ""

            if hasattr(message, "facts"):
                facts_lines = self._format_lines(getattr(message, "facts"))
                if facts_lines:
                    sections.append(("Facts", facts_lines))

            if hasattr(message, "plan"):
                plan_lines = self._format_lines(getattr(message, "plan"))
                if plan_lines:
                    sections.append(("Plan", plan_lines))

            if hasattr(message, "status"):
                status = getattr(message, "status")
                if status is not None:
                    sections.append(("Status", [str(status)]))

            if hasattr(message, "content") and getattr(message, "content"):
                raw_output = str(getattr(message, "content"))
            else:
                raw_output = str(getattr(message, "raw_text", "")) or ""

            if not sections:
                content_lines = self._format_lines(raw_output)
                sections.append(("Result", content_lines))

        if not sections:
            sections = [("Result", ["(none)"])]

        for index, (title, lines) in enumerate(sections):
            pretty = [f"  {line}" for line in lines] if lines else ["  (none)"]
            self._print_section(title, pretty, pre_blank=index != 0)

        if raw_output and raw_output.strip():
            self.console.print(Text("Raw Output", style="bold"))
            self.console.print(Text(self._divider, style="dim"))
            self.console.print(raw_output)
            self.console.print()

    @staticmethod
    def _format_lines(
        value: str | Iterable[str | dict[str, Any]] | dict[str, Any] | None,
    ) -> list[str]:
        """Normalize various inputs to a list of displayable strings."""

        if value is None:
            return ["(none)"]

        if isinstance(value, str):
            normalized = value.replace("\\n", "\n")
            stripped = [v.strip().strip("'\"") for v in normalized.splitlines() if v.strip()]
            return stripped or ["(none)"]

        if isinstance(value, dict):
            return [f"{key}: {val}" for key, val in value.items()]

        if isinstance(value, Sequence):
            lines: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    lines.extend(f"{key}: {val}" for key, val in item.items())
                elif item is None:
                    continue
                else:
                    text = str(item).strip()
                    if text:
                        lines.extend(ConsoleUI._format_lines(text))
            return lines or ["(none)"]

        text = str(value).strip()
        return ConsoleUI._format_lines(text) if text else ["(none)"]

    def _print_section(
        self,
        title: str,
        lines: Iterable[str],
        *,
        pre_blank: bool = True,
        style: str | None = None,
    ) -> None:
        """Render a titled section with optional styling."""

        if pre_blank:
            self.console.print()

        header_style = "bold" if style is None else f"bold {style}"
        self.console.print(Text(title, style=header_style))
        self.console.print(Text(self._divider, style="dim"))

        for line in lines:
            if style:
                self.console.print(Text(line, style=style))
            else:
                self.console.print(line)

        self.console.print()
