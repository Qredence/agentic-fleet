"""Display utilities for CLI output.

This module provides Rich-based formatting utilities for displaying
workflow results, tables, and status information.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ..cli.runner import WorkflowRunner


def display_result(result: dict[str, Any], console: Console | None = None) -> None:
    """Display workflow result in formatted output with reasoning steps and final answer.

    Args:
        result: Workflow result dictionary
        console: Rich console instance (creates new if None)
    """
    if console is None:
        console = Console()

    if not result:
        console.print("[yellow]No result to display[/yellow]")
        return

    # Extract result data
    result_text = str(result.get("result", "No result"))
    metadata = result.get("metadata", {})

    # 1. Show Reasoning Steps (if available in execution summary)
    execution_summary = metadata.get("execution_summary", {})
    routing_history = execution_summary.get("routing_history", [])

    if routing_history:
        console.print("\n" + "=" * 80)
        console.print("[bold cyan]🧠 REASONING & EXECUTION STEPS[/bold cyan]")
        console.print("=" * 80 + "\n")

        for i, routing in enumerate(routing_history, 1):
            step_mode = routing.get("mode", "unknown")
            step_agents = ", ".join(routing.get("assigned_to", []))
            step_confidence = routing.get("confidence", 0.0)

            console.print(
                Panel(
                    f"[bold]Mode:[/bold] {step_mode}\n"
                    f"[bold]Agents:[/bold] {step_agents}\n"
                    f"[bold]Confidence:[/bold] {step_confidence:.2f}",
                    title=f"[bold yellow]Step {i}[/bold yellow]",
                    border_style="yellow",
                )
            )

    # 2. Show Judge Evaluations (if available)
    judge_evaluations = metadata.get("judge_evaluations", [])
    if judge_evaluations:
        console.print("\n" + "=" * 80)
        console.print("[bold magenta]⚖️  QUALITY ASSESSMENTS[/bold magenta]")
        console.print("=" * 80 + "\n")

        for i, judge_eval in enumerate(judge_evaluations, 1):
            score = judge_eval.get("score", 0.0)
            reasoning = judge_eval.get("reasoning", "No reasoning provided")
            improvements = judge_eval.get("improvements", "No improvements suggested")

            console.print(
                Panel(
                    f"[bold]Score:[/bold] {score}/10\n\n"
                    f"[bold]Reasoning:[/bold]\n{reasoning}\n\n"
                    f"[bold]Improvements:[/bold]\n{improvements}",
                    title=f"[bold magenta]Assessment {i}[/bold magenta]",
                    border_style="magenta",
                )
            )

    # 3. Show Phase Timings
    phase_timings = metadata.get("phase_timings", {})
    if phase_timings:
        console.print("\n" + "=" * 80)
        console.print("[bold blue]⏱️  EXECUTION TIMINGS[/bold blue]")
        console.print("=" * 80 + "\n")

        timing_table = Table(show_header=True, header_style="bold blue")
        timing_table.add_column("Phase", style="cyan")
        timing_table.add_column("Duration", justify="right", style="green")

        for phase, duration in sorted(phase_timings.items(), key=lambda x: x[1], reverse=True):
            timing_table.add_row(phase, f"{duration:.2f}s")

        console.print(timing_table)

    # 4. Show FINAL ANSWER prominently
    console.print("\n" + "=" * 80)
    console.print("[bold green]✅ FINAL ANSWER[/bold green]")
    console.print("=" * 80 + "\n")

    console.print(
        Panel(
            Markdown(result_text),
            title="[bold green]🎯 Result[/bold green]",
            border_style="bold green",
            padding=(1, 2),
        )
    )

    # 5. Show Quality Score
    if "quality" in metadata:
        quality = metadata["quality"]
        quality_score = quality.get("score", 0.0)

        # Color based on score
        if quality_score >= 8:
            score_style = "bold green"
            emoji = "🌟"
        elif quality_score >= 6:
            score_style = "bold yellow"
            emoji = "⭐"
        else:
            score_style = "bold red"
            emoji = "⚠️"

        console.print(
            Panel(
                f"[{score_style}]{emoji} Quality Score: {quality_score}/10[/{score_style}]",
                border_style=score_style.split()[-1],
            )
        )

    # 6. Show Execution Metadata
    # Prefer top-level routing info, fall back to metadata
    routing_data = result.get("routing") or metadata.get("routing")

    if routing_data:
        # Handle RoutingDecision objects if present
        if hasattr(routing_data, "to_dict"):
            routing = routing_data.to_dict()
        elif isinstance(routing_data, dict):
            routing = routing_data
        else:
            routing = {}

        if routing:
            # Handle key variations (assigned_to vs agents)
            agents_list = routing.get("assigned_to") or routing.get("agents") or []

            exec_info = (
                f"[bold]Execution Mode:[/bold] {routing.get('mode', 'unknown')}\n"
                f"[bold]Agents Used:[/bold] {', '.join(agents_list)}\n"
                f"[bold]Confidence:[/bold] {routing.get('confidence', 0.0) or 0.0:.2f}"
            )

            if "execution_time" in metadata:
                exec_info += f"\n[bold]Total Time:[/bold] {metadata['execution_time']:.2f}s"

            console.print(
                Panel(
                    exec_info,
                    title="[bold blue]📊 Execution Details[/bold blue]",
                    border_style="blue",
                )
            )

    console.print("\n" + "=" * 80 + "\n")


def show_help(console: Console | None = None) -> None:
    """Show interactive mode help.

    Args:
        console: Rich console instance (creates new if None)
    """
    if console is None:
        console = Console()

    help_text = """
[bold]Available Commands:[/bold]
  • exit, quit - Exit the console
  • clear - Clear the screen
  • help - Show this help message
  • status - Show workflow status

[bold]Example Tasks:[/bold]
  • "Analyze the impact of AI on healthcare"
  • "Write a blog post about quantum computing"
  • "Research and compare cloud providers"
  • "Create a financial analysis of Tesla stock"

[bold]Tips:[/bold]
  • Be specific in your requests for better results
  • Complex tasks will be automatically broken down
  • Use streaming mode to see real-time progress
    """

    console.print(Panel(help_text, title="Help", border_style="cyan"))


def show_status(runner: WorkflowRunner, console: Console | None = None) -> None:
    """Show current workflow status.

    Args:
        runner: WorkflowRunner instance
        console: Rich console instance (creates new if None)
    """
    if console is None:
        console = Console()

    if not runner.workflow:
        console.print("[yellow]No workflow initialized yet[/yellow]")
        return

    if runner.workflow.dspy_supervisor is None:
        console.print("[yellow]DSPy supervisor not initialized[/yellow]")
        return

    summary = runner.workflow.dspy_supervisor.get_execution_summary()

    status_text = f"""
[bold]Workflow Status:[/bold]
  • Model: {runner.workflow.config.dspy_model}
  • DSPy Compiled: {runner.workflow.config.compile_dspy}
  • Completion Storage: {runner.workflow.config.enable_completion_storage}
  • Total Routings: {summary["total_routings"]}
  • Max Rounds: {runner.workflow.config.max_rounds}
  • Refinement Threshold: {runner.workflow.config.refinement_threshold}
    """

    if summary["routing_history"]:
        status_text += "\n\n[bold]Recent Routings:[/bold]\n"
        for routing in summary["routing_history"][-3:]:
            status_text += f"  • {routing['mode']} → {', '.join(routing['assigned_to'])}\n"

    console.print(Panel(status_text, title="Status", border_style="blue"))
