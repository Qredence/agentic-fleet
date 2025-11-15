"""Handoff command for agent-to-agent handoffs."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from ...utils.logger import setup_logger
from ..runner import WorkflowRunner
from ..utils import init_tracing

console = Console()


def handoff(
    interactive: bool = typer.Option(False, "--interactive", help="Interactive handoff session"),
    compile_dspy: bool = typer.Option(True, "--compile", help="Compile DSPy modules"),
    model: str | None = typer.Option(None, "--model", help="Override model ID"),
) -> None:
    """Handoff-centric workflow mode.

    Explore and create agent-to-agent handoffs with the HandoffManager.

    Examples:
      console.py handoff            # start interactive session
      console.py handoff --no-interactive  # just initialize (useful for smoke tests)
    """
    setup_logger("dspy_agent_framework", "INFO")
    init_tracing()

    async def start_session() -> None:
        runner = WorkflowRunner(verbose=False)
        await runner.initialize_workflow(
            compile_dspy=compile_dspy, model=model, enable_handoffs=True
        )

        wf = runner.workflow
        assert wf is not None
        wf.enable_handoffs = True  # ensure on regardless of defaults

        if not wf.handoff_manager:
            console.print("[red]HandoffManager not available[/red]")
            return

        agents = wf.agents or {}
        if not agents:
            console.print("[red]No agents are registered in the workflow.[/red]")
            return

        # Show agents and quick help
        agents_list = ", ".join(agents.keys())
        console.print(
            Panel(
                f"[bold]Handoff Mode[/bold]\nAgents: {agents_list}\n\n"
                "Enter 'exit' to quit, 'help' for available agents.\n"
                "Press enter on any prompt to skip.",
                title="Handoff Session",
                border_style="blue",
            )
        )

        if not interactive:
            return

        # Create case-insensitive agent lookup
        agent_lookup = {name.lower(): name for name in agents}

        while True:
            from_agent_input = console.input("From agent> ").strip()

            # Check for exit
            if from_agent_input.lower() in {"exit", "quit"}:
                break

            # Check for help
            if from_agent_input.lower() == "help":
                console.print(f"[cyan]Available agents: {agents_list}[/cyan]")
                continue

            # Skip empty input
            if not from_agent_input:
                continue

            # Case-insensitive agent lookup
            from_agent = agent_lookup.get(from_agent_input.lower())

            if not from_agent:
                console.print(
                    f"[yellow]Unknown agent '{from_agent_input}'. "
                    f"Available agents: {agents_list}[/yellow]"
                )
                continue

            remaining_work = console.input("Describe remaining work> ").strip()
            work_completed = console.input("Summarize completed work> ").strip()

            # Available agents map (exclude current)
            available = {
                name: getattr(agent, "description", name)
                for name, agent in agents.items()
                if name != from_agent
            }

            next_agent = await wf.handoff_manager.evaluate_handoff(
                current_agent=from_agent,
                work_completed=work_completed,
                remaining_work=remaining_work,
                available_agents=available,
            )

            if next_agent:
                console.print(f"[green]Recommended → {next_agent}[/green]")
                do_pkg = console.input("Create handoff package? [y/N]> ").strip().lower()
                if do_pkg in {"y", "yes"}:
                    raw_objectives = console.input("Objectives (semicolon-separated)> ").strip()
                    remaining_objectives = [
                        o.strip() for o in raw_objectives.split(";") if o.strip()
                    ] or [remaining_work]

                    pkg = await wf.handoff_manager.create_handoff_package(
                        from_agent=from_agent,
                        to_agent=next_agent,
                        work_completed=work_completed,
                        artifacts={},
                        remaining_objectives=remaining_objectives,
                        task=remaining_work or "User task",
                        handoff_reason="manual handoff via console",
                    )

                    preview = wf._format_handoff_input(pkg)  # re-use formatter
                    console.print(Panel(preview, title="Handoff Package", border_style="green"))
            else:
                console.print("[yellow]No handoff recommended.[/yellow]")

    asyncio.run(start_session())
