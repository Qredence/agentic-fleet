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

from agentic_fleet.utils.cfg import DEFAULT_EXAMPLES_PATH

from ..utils.self_improvement import SelfImprovementEngine

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

    stats_table.add_row("Total Executions", str(stats["total_executions"]))
    stats_table.add_row(
        "High-Quality Executions",
        f"{stats['high_quality_executions']} ({stats['high_quality_executions'] / max(stats['total_executions'], 1) * 100:.1f}%)",
    )
    stats_table.add_row("Potential New Examples", str(stats["potential_new_examples"]))
    stats_table.add_row("Quality Threshold", f"{stats['min_quality_threshold']}/10")
    stats_table.add_row("Average Quality Score", f"{stats['average_quality_score']:.2f}/10")

    console.print(stats_table)

    # Show quality distribution
    console.print("\n[bold]Quality Score Distribution:[/bold]")
    dist = stats["quality_score_distribution"]
    for category, count in dist.items():
        console.print(f"  • {category}: {count}")

    if args.stats_only:
        console.print("\n[dim]Run without --stats-only to add examples[/dim]")
        return

    # Perform self-improvement
    if stats["high_quality_executions"] == 0:
        console.print("\n[yellow]⚠ No high-quality executions found to learn from[/yellow]")
        console.print(
            f"[dim]Tip: Lower --min-quality threshold (current: {args.min_quality})[/dim]"
        )
        return

    console.print("\n[bold cyan]🔄 Generating Training Examples...[/bold cyan]")

    added, status = engine.auto_improve(
        examples_file=args.examples_file, force_recompile=not args.no_recompile
    )

    if added > 0:
        console.print(
            Panel(
                f"[bold green]✓ Success![/bold green]\n\n"
                f"{status}\n\n"
                f"Added {added} new training examples from high-quality executions.\n"
                f"Next execution will use the improved routing model.",
                title="Self-Improvement Complete",
                border_style="green",
            )
        )

        console.print(
            "\n[bold]Next steps:[/bold]\n"
            f"  1. Review new examples: [cyan]cat {DEFAULT_EXAMPLES_PATH} | tail -50[/cyan]\n"
            '  2. Test improved routing: [cyan]python console.py run -m "Test task"[/cyan]\n'
            "  3. Monitor quality scores in future executions"
        )
    else:
        console.print(
            Panel(
                "[yellow]No new examples added[/yellow]\n\n"
                "All high-quality executions are already in training set.",
                title="Self-Improvement",
                border_style="yellow",
            )
        )


if __name__ == "__main__":
    main()
