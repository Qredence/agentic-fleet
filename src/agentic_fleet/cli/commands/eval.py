"""Eval commands: benchmark, evaluate.

Consolidated from benchmark.py, evaluate.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...evaluation import Evaluator
from ...utils.cfg import load_config
from ..runner import WorkflowRunner
from ..utils import init_tracing, resolve_resource_path

console = Console()

# -----------------------------------------------------------------------------
# benchmark
# -----------------------------------------------------------------------------


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
        results: dict[str, list[float]] = {"compiled": [], "uncompiled": []}

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

        console.print("\n[bold blue]Testing without DSPy compilation...[/bold blue]")
        runner_uncompiled = WorkflowRunner()
        await runner_uncompiled.initialize_workflow(compile_dspy=False)

        for i in range(iterations):
            start = datetime.now()
            await runner_uncompiled.run_without_streaming(task)
            elapsed = (datetime.now() - start).total_seconds()
            results["uncompiled"].append(elapsed)
            console.print(f"  Iteration {i + 1}: {elapsed:.2f}s")

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

        avg_uncompiled = None
        if results["uncompiled"]:
            avg_uncompiled = sum(results["uncompiled"]) / len(results["uncompiled"])
            table.add_row(
                "Uncompiled",
                f"{avg_uncompiled:.2f}",
                f"{min(results['uncompiled']):.2f}",
                f"{max(results['uncompiled']):.2f}",
            )
        else:
            table.add_row("Uncompiled", "N/A", "N/A", "N/A")

        console.print("\n")
        console.print(table)

        if (
            results["compiled"]
            and avg_compiled is not None
            and avg_uncompiled is not None
            and avg_uncompiled > 0
        ):
            improvement = ((avg_uncompiled - avg_compiled) / avg_uncompiled) * 100
            console.print(
                f"\n[bold green]Compilation improved performance by {improvement:.1f}%[/bold green]"
            )

    asyncio.run(run_benchmark())


# -----------------------------------------------------------------------------
# evaluate
# -----------------------------------------------------------------------------


def evaluate(
    dataset: Annotated[
        Path | None,
        typer.Option("--dataset", "-d", help="Override dataset path (defaults to config)"),
    ] = None,
    max_tasks: Annotated[
        int, typer.Option("--max-tasks", help="Limit number of tasks (0 = all)")
    ] = 0,
    metrics: Annotated[
        str | None,
        typer.Option(
            "--metrics",
            help=(
                "Comma-separated metric list overriding config "
                "(quality_score,keyword_success,latency_seconds,routing_efficiency,refinement_triggered)"
            ),
        ),
    ] = None,
    stop_on_failure: Annotated[
        bool, typer.Option("--stop-on-failure", help="Stop when a *success* metric returns 0/None")
    ] = False,
) -> None:
    """Run batch evaluation over a dataset using configured metrics."""
    init_tracing()
    cfg = load_config()
    eval_cfg = cfg.get("evaluation", {})
    if not eval_cfg.get("enabled", True):
        console.print(
            "[yellow]Evaluation disabled in config. Enable 'evaluation.enabled'.[/yellow]"
        )
        raise typer.Exit(1)

    dataset_path = str(
        resolve_resource_path(
            dataset or Path(eval_cfg.get("dataset_path", "data/evaluation_tasks.jsonl"))
        )
    )
    metric_list = (
        [m.strip() for m in metrics.split(",") if m.strip()]
        if metrics
        else eval_cfg.get("metrics", [])
    )
    out_dir = eval_cfg.get("output_dir", ".var/logs/evaluation")
    max_tasks_effective = max_tasks if max_tasks else int(eval_cfg.get("max_tasks", 0))
    stop = stop_on_failure or bool(eval_cfg.get("stop_on_failure", False))

    async def wf_factory():
        runner = WorkflowRunner(verbose=False)
        await runner.initialize_workflow(
            compile_dspy=cfg.get("dspy", {}).get("optimization", {}).get("enabled", True)
        )
        if runner.workflow is None:
            raise RuntimeError("WorkflowRunner failed to initialize workflow")
        return runner.workflow

    evaluator = Evaluator(
        workflow_factory=wf_factory,
        dataset_path=dataset_path,
        output_dir=out_dir,
        metrics=metric_list,
        max_tasks=max_tasks_effective,
        stop_on_failure=stop,
    )

    console.print(
        Panel(
            f"[bold]Starting Evaluation[/bold]\nDataset: {dataset_path}\nMetrics: {
                ', '.join(metric_list) if metric_list else 'None'
            }",
            title="Evaluation",
            border_style="magenta",
        )
    )

    async def run_eval():
        summary = await evaluator.run()
        console.print(
            Panel(
                f"Total Tasks: {summary['total_tasks']}\nMetric Means: "
                + ", ".join(
                    f"{k}={v['mean']:.2f}"
                    for k, v in summary.get("metrics", {}).items()
                    if v.get("mean") is not None
                ),
                title="Evaluation Summary",
                border_style="green",
            )
        )
        console.print(
            f"[dim]Report: {out_dir}/evaluation_report.jsonl | Summary: {out_dir}/evaluation_summary.json[/dim]"
        )

    asyncio.run(run_eval())
