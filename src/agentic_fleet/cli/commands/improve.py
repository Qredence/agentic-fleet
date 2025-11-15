"""Improve command for self-improvement."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from ...utils.self_improvement import SelfImprovementEngine
from ..utils import init_tracing

console = Console()


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

    # Tracing initialization (optional)
    init_tracing()

    # Show stats
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

    # Perform improvement
    added, status = engine.auto_improve()

    if added > 0:
        console.print(f"\n[green]✓ {status}[/green]")
        console.print("[dim]Next execution will use improved routing model[/dim]")
    else:
        console.print(f"\n[yellow]{status}[/yellow]")
