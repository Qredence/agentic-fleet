"""Analyze command for task analysis."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from ..runner import WorkflowRunner
from ..utils import init_tracing

console = Console()


def analyze(
    task: str = typer.Argument(..., help="Task to analyze"),
    show_routing: bool = typer.Option(True, "--routing/--no-routing", help="Show routing decision"),
    compile_dspy: bool = typer.Option(True, "--compile/--no-compile", help="Compile DSPy module"),
) -> None:
    """
    Analyze a task using DSPy supervisor without execution.

    Shows how the task would be routed and processed.
    """

    async def analyze_task() -> None:
        init_tracing()
        runner = WorkflowRunner()
        await runner.initialize_workflow(compile_dspy=compile_dspy)

        workflow = runner.workflow
        if workflow is None:
            console.print("[red]Workflow failed to initialize.[/red]")
            raise typer.Exit(code=1)

        supervisor = workflow.dspy_reasoner
        if supervisor is None:
            console.print("[red]DSPy reasoner is unavailable.[/red]")
            raise typer.Exit(code=1)

        # Analyze task
        analysis = supervisor.analyze_task(task)

        # Get routing decision
        routing = supervisor.forward(
            task=task,
            team_capabilities="Researcher: Web research, Analyst: Data analysis, Writer: Content creation, Reviewer: Quality check",
        )

        # Display analysis
        table = Table(title="Task Analysis", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Complexity", analysis["complexity"])
        table.add_row("Estimated Steps", str(analysis["steps"]))
        table.add_row("Required Capabilities", ", ".join(analysis["capabilities"]))

        console.print(table)

        if show_routing:
            # Display routing
            routing_table = Table(
                title="Routing Decision", show_header=True, header_style="bold blue"
            )
            routing_table.add_column("Property", style="cyan")
            routing_table.add_column("Value", style="green")

            mode_display = getattr(routing.mode, "value", routing.mode)
            routing_table.add_row("Execution Mode", str(mode_display))
            routing_table.add_row("Assigned Agents", ", ".join(routing.assigned_to))
            confidence_display = (
                f"{routing.confidence:.2f}" if routing.confidence is not None else "n/a"
            )
            routing_table.add_row("Confidence", confidence_display)

            if routing.subtasks:
                routing_table.add_row("Subtasks", "\n".join(routing.subtasks[:3]))

            console.print("\n")
            console.print(routing_table)

    asyncio.run(analyze_task())
