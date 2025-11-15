"""Evaluate command for batch evaluation."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from ...evaluation import Evaluator
from ...utils.config_loader import load_config
from ..runner import WorkflowRunner
from ..utils import resolve_resource_path

console = Console()


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
    cfg = load_config()
    eval_cfg = cfg.get("evaluation", {})
    if not eval_cfg.get("enabled", True):
        console.print(
            "[yellow]Evaluation disabled in config. Enable 'evaluation.enabled'.[/yellow]"
        )
        raise typer.Exit(1)

    # Resolve dataset path robustly (CWD first, then packaged data)
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
    out_dir = eval_cfg.get("output_dir", "logs/evaluation")
    max_tasks_effective = max_tasks if max_tasks else int(eval_cfg.get("max_tasks", 0))
    stop = stop_on_failure or bool(eval_cfg.get("stop_on_failure", False))

    async def wf_factory():
        runner = WorkflowRunner(verbose=False)
        await runner.initialize_workflow(
            compile_dspy=cfg.get("dspy", {}).get("optimization", {}).get("enabled", True)
        )
        assert runner.workflow is not None
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
