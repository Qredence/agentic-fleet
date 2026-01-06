#!/usr/bin/env python3
"""
Self-improvement script for DSPy-Agent-Framework.

Analyzes execution history and automatically generates new training examples
from high-quality executions to improve future routing decisions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_fleet.dspy_modules.optimization import SelfImprovementEngine
from agentic_fleet.utils.cfg import DEFAULT_EXAMPLES_PATH

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


console = Console()


def main():
    """Run the self-improvement process."""
    parser = argparse.ArgumentParser(description="Self-improve DSPy routing from execution history")
    parser.add_argument(
        "--min-quality",
        type=float,
        default=7.0,
        help="Minimum quality score for examples (0-10)",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=20,
        help="Maximum new examples to add",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=100,
        help="Number of recent executions to analyze",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Show statistics without adding examples",
    )
    parser.add_argument(
        "--examples-file",
        type=str,
        default=DEFAULT_EXAMPLES_PATH,
        help="Path to training examples file",
    )
    parser.add_argument(
        "--no-recompile",
        action="store_true",
        help="Don't clear cache (skip forced recompilation)",
    )

    args = parser.parse_args()

    # Create engine
    engine = SelfImprovementEngine(
        min_quality_score=args.min_quality,
        max_examples_to_add=args.max_examples,
        history_lookback=args.lookback,
    )

    # Show statistics
    console.print("\n[bold cyan]📊 Self-Improvement Analysis[/bold cyan]\n")

    stats = engine.get_improvement_stats()

    # Create statistics table
    stats_table = Table(title="Execution History Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")

    total: int = stats.get("total_executions", 0)
    hq_count: int = stats.get("high_quality_executions", 0)
    hq_pct: float = hq_count / max(total, 1) * 100

    stats_table.add_row("Total Executions", str(total))
    stats_table.add_row(
        "High-Quality Executions",
        f"{hq_count} ({hq_pct:.1f}%)",
    )
    stats_table.add_row("Potential New Examples", str(stats.get("potential_new_examples", 0)))
    stats_table.add_row(
        "Quality Threshold", f"{stats.get('min_quality_threshold', args.min_quality)}/10"
    )
    stats_table.add_row("Average Quality Score", f"{stats.get('average_quality_score', 0):.2f}/10")

    console.print(stats_table)

    # Show quality distribution
    console.print("\n[bold]Quality Score Distribution:[/bold]")
    dist = stats.get("quality_score_distribution", {})
    if not dist:
        console.print("[dim]No quality data available[/dim]")
    else:
        dist_table = Table()
        dist_table.add_column("Range", style="yellow")
        dist_table.add_column("Count", style="white")

        for k, v in dist.items():
            dist_table.add_row(k, str(v))
        console.print(dist_table)

    if args.stats_only:
        return

    # Proceed with improvement if there are potential examples
    if stats.get("potential_new_examples", 0) > 0:
        console.print("\n[bold green]🚀 Running Improvement Process...[/bold green]")
        _added, message = engine.auto_improve(
            examples_file=args.examples_file,
            force_recompile=not args.no_recompile,
        )
        console.print(Panel(message, title="Result", border_style="green"))
    else:
        console.print("\n[yellow]No additional high-quality examples found to add.[/yellow]")


if __name__ == "__main__":
    main()
