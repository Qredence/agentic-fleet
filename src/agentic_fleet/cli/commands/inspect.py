"""Inspect commands: agents, history, analyze, improve.

Consolidated from agents.py, history.py, analyze.py, improve.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agentic_fleet.cli.runner import WorkflowRunner
from agentic_fleet.cli.utils import init_tracing
from agentic_fleet.utils.cfg import env_config
from agentic_fleet.utils.self_improvement import SelfImprovementEngine

console = Console()

# -----------------------------------------------------------------------------
# agents (list-agents)
# -----------------------------------------------------------------------------


def list_agents() -> None:
    """List all available agents and their capabilities."""
    tavily_available = bool(env_config.tavily_api_key)

    agents_info = [
        {
            "name": "Researcher",
            "description": "Information gathering and web research specialist",
            "tools": [
                f"TavilySearchTool {'(enabled)' if tavily_available else '(missing TAVILY_API_KEY)'}"
            ],
            "best_for": "Finding information, fact-checking, research",
        },
        {
            "name": "Analyst",
            "description": "Data analysis and computation specialist",
            "tools": ["HostedCodeInterpreterTool"],
            "best_for": "Data analysis, calculations, visualizations",
        },
        {
            "name": "Writer",
            "description": "Content creation and report writing specialist",
            "tools": ["None"],
            "best_for": "Writing, documentation, content creation",
        },
        {
            "name": "Reviewer",
            "description": "Quality assurance and validation specialist",
            "tools": ["None"],
            "best_for": "Review, validation, quality checks",
        },
    ]

    table = Table(title="Available Agents", show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan", width=12)
    table.add_column("Description", style="yellow", width=40)
    table.add_column("Tools", style="green", width=30)
    table.add_column("Best For", style="blue", width=30)

    for agent in agents_info:
        tools_str = ", ".join(agent["tools"])
        table.add_row(
            str(agent["name"]),
            str(agent["description"]),
            str(tools_str),
            str(agent["best_for"]),
        )

    console.print(table)


# -----------------------------------------------------------------------------
# history (export-history)
# -----------------------------------------------------------------------------


def export_history(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file path"),
    ] = Path("workflow_history.json"),
    task: Annotated[str, typer.Option("--task", "-t", help="Task to run before export")] = "",
    model: Annotated[
        str, typer.Option("--model", help="Model to use for task execution")
    ] = "gpt-4.1-mini",
) -> None:
    """Export workflow execution history to a file."""

    async def export() -> None:
        init_tracing()
        runner = WorkflowRunner()
        await runner.initialize_workflow(model=model)

        if task:
            console.print(f"[bold blue]Running task: {task}[/bold blue]")
            await runner.run_without_streaming(task)

        assert runner.workflow is not None, "Workflow not initialized"
        assert runner.workflow.dspy_supervisor is not None, "DSPy supervisor not initialized"

        summary = runner.workflow.dspy_supervisor.get_execution_summary()

        export_data = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "execution_summary": summary,
            "config": {
                "model": runner.workflow.config.dspy_model,
                "compiled": runner.workflow.config.compile_dspy,
                "completion_storage": runner.workflow.config.enable_completion_storage,
                "refinement_threshold": runner.workflow.config.refinement_threshold,
            },
        }

        with open(output, "w") as f:
            json.dump(export_data, f, indent=2)

        console.print(f"[bold green]✓ Exported history to {output}[/bold green]")

    asyncio.run(export())


# -----------------------------------------------------------------------------
# analyze
# -----------------------------------------------------------------------------


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

        analysis = supervisor.analyze_task(task)

        routing = supervisor.forward(
            task=task,
            team_capabilities="Researcher: Web research, Analyst: Data analysis, Writer: Content creation, Reviewer: Quality check",
        )

        table = Table(title="Task Analysis", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Complexity", analysis["complexity"])
        table.add_row("Estimated Steps", str(analysis["steps"]))
        table.add_row("Required Capabilities", ", ".join(analysis["capabilities"]))

        console.print(table)

        if show_routing:
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


# -----------------------------------------------------------------------------
# self-improve
# -----------------------------------------------------------------------------


def self_improve(
    min_quality: float = typer.Option(
        8.0, "--min-quality", "-q", help="Minimum quality score (0-10)"
    ),
    max_examples: int = typer.Option(20, "--max-examples", "-n", help="Maximum examples to add"),
    stats_only: bool = typer.Option(
        False, "--stats-only", help="Show stats without adding examples"
    ),
) -> None:
    """Automatically improve routing from high-quality execution history."""
    engine = SelfImprovementEngine(
        min_quality_score=min_quality,
        max_examples_to_add=max_examples,
        history_lookback=100,
    )

    init_tracing()

    stats = engine.get_improvement_stats()

    console.print("\n[bold cyan]📊 Self-Improvement Analysis[/bold cyan]\n")

    stats_table = Table()
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")

    stats_table.add_row("Total Executions", str(stats["total_executions"]))
    stats_table.add_row("High-Quality Executions", str(stats["high_quality_executions"]))
    stats_table.add_row("Average Quality Score", f"{stats['average_quality_score']:.2f}/10")

    console.print(stats_table)

    if stats_only:
        return

    if stats["high_quality_executions"] == 0:
        console.print("\n[yellow]⚠ No high-quality executions to learn from[/yellow]")
        return

    added, status = engine.auto_improve()

    if added > 0:
        console.print(f"\n[green]✓ {status}[/green]")
        console.print("[dim]Next execution will use improved routing model[/dim]")
    else:
        console.print(f"\n[yellow]{status}[/yellow]")
