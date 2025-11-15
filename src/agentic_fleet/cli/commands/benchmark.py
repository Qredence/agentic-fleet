"""Benchmark command for performance testing."""

from __future__ import annotations

import asyncio
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from ..runner import WorkflowRunner
from ..utils import init_tracing

console = Console()


def benchmark(
    task: str = typer.Option(
        "Write a blog post about AI", "--task", "-t", help="Task to benchmark"
    ),
    iterations: int = typer.Option(3, "--iterations", "-n", help="Number of iterations"),
    compile_dspy: bool = typer.Option(True, "--compile/--no-compile", help="Compile DSPy module"),
) -> None:
    """
    Benchmark workflow performance with and without DSPy compilation.
    """

    async def run_benchmark() -> None:
        init_tracing()
        results = {"compiled": [], "uncompiled": []}

        # Test with compilation
        if compile_dspy:
            console.print("[bold blue]Testing with DSPy compilation...[/bold blue]")
            runner_compiled = WorkflowRunner()
            await runner_compiled.initialize_workflow(compile_dspy=True)

            for i in range(iterations):
                start = datetime.now()
                await runner_compiled.run_without_streaming(task)
                elapsed = (datetime.now() - start).total_seconds()
                results["compiled"].append(elapsed)
                console.print(f"  Iteration {i + 1}: {elapsed:.2f}s")

        # Test without compilation
        console.print("\n[bold blue]Testing without DSPy compilation...[/bold blue]")
        runner_uncompiled = WorkflowRunner()
        await runner_uncompiled.initialize_workflow(compile_dspy=False)

        for i in range(iterations):
            start = datetime.now()
            await runner_uncompiled.run_without_streaming(task)
            elapsed = (datetime.now() - start).total_seconds()
            results["uncompiled"].append(elapsed)
            console.print(f"  Iteration {i + 1}: {elapsed:.2f}s")

        # Display results
        table = Table(title="Benchmark Results", show_header=True)
        table.add_column("Mode", style="cyan")
        table.add_column("Avg Time (s)", style="yellow")
        table.add_column("Min Time (s)", style="green")
        table.add_column("Max Time (s)", style="red")

        avg_compiled = None
        if results["compiled"]:
            avg_compiled = sum(results["compiled"]) / len(results["compiled"])
            table.add_row(
                "Compiled",
                f"{avg_compiled:.2f}",
                f"{min(results['compiled']):.2f}",
                f"{max(results['compiled']):.2f}",
            )

        avg_uncompiled = sum(results["uncompiled"]) / len(results["uncompiled"])
        table.add_row(
            "Uncompiled",
            f"{avg_uncompiled:.2f}",
            f"{min(results['uncompiled']):.2f}",
            f"{max(results['uncompiled']):.2f}",
        )

        console.print("\n")
        console.print(table)

        if results["compiled"] and avg_compiled is not None:
            improvement = ((avg_uncompiled - avg_compiled) / avg_uncompiled) * 100
            console.print(
                f"\n[bold green]Compilation improved performance by {improvement:.1f}%[/bold green]"
            )

    asyncio.run(run_benchmark())
