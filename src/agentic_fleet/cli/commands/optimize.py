"""Optimize command for GEPA optimization."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

from ...dspy_modules.supervisor import DSPySupervisor
from ...utils.compiler import compile_supervisor
from ...utils.config_loader import load_config
from ...utils.tool_registry import ToolRegistry
from ..utils import init_tracing, resolve_resource_path

console = Console()


def gepa_optimize(
    examples: Path = typer.Option(
        Path("data/supervisor_examples.json"),
        "--examples",
        "-e",
        help="Training dataset path",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Model for DSPy LM (defaults to config dspy.model)",
    ),
    auto: str | None = typer.Option(
        None,
        "--auto",
        help="GEPA auto configuration (light|medium|heavy). Mutually exclusive with --max-full-evals / --max-metric-calls. If omitted, you MUST provide one numeric limit.",
        case_sensitive=False,
    ),
    max_full_evals: int | None = typer.Option(
        None,
        "--max-full-evals",
        help="Explicit full GEPA evaluation budget (exclusive with --auto / --max-metric-calls)",
    ),
    max_metric_calls: int | None = typer.Option(
        None,
        "--max-metric-calls",
        help="Explicit metric call budget (exclusive with --auto / --max-full-evals)",
    ),
    reflection_model: str | None = typer.Option(
        None,
        "--reflection-model",
        help="Optional LM for reflections (defaults to main LM)",
    ),
    val_split: float = typer.Option(0.2, "--val-split", help="Validation split (0.0-0.5)"),
    use_history: bool = typer.Option(
        False,
        "--use-history/--no-history",
        help="Augment training data with high-quality execution history",
    ),
    history_min_quality: float = typer.Option(
        8.0, "--history-min-quality", help="Minimum quality score for harvested history"
    ),
    history_limit: int = typer.Option(200, "--history-limit", help="History lookback size"),
    log_dir: Path = typer.Option(Path("logs/gepa"), "--log-dir", help="Directory for GEPA logs"),
    seed: int = typer.Option(13, "--seed", help="Random seed for dataset shuffle"),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Do not read/write compiled module cache (always recompile)",
    ),
) -> None:
    """
    Compile the DSPy supervisor using dspy.GEPA for prompt evolution.
    """
    yaml_config = load_config()
    effective_model = model or yaml_config.get("dspy", {}).get("model", "gpt-5-mini")
    # Resolve examples against CWD then packaged data if needed
    examples = resolve_resource_path(examples)

    # Initialize tracing prior to GEPA to capture compilation spans if supported
    init_tracing()

    console.print(
        Panel(
            f"[bold]Running GEPA[/bold]\nModel: {effective_model}\nDataset: {examples}",
            title="dspy.GEPA Optimization",
            border_style="magenta",
        )
    )

    auto_choice = auto.lower() if auto else None
    if auto_choice and auto_choice not in {"light", "medium", "heavy"}:
        raise typer.BadParameter("--auto must be one of: light, medium, heavy")
    if not 0.0 <= val_split <= 0.5:
        raise typer.BadParameter("--val-split must be between 0.0 and 0.5")
    if not 0.0 <= history_min_quality <= 10.0:
        raise typer.BadParameter("--history-min-quality must be between 0 and 10")

    # Enforce exclusivity: exactly ONE of auto_choice, max_full_evals, max_metric_calls
    chosen = [c for c in [auto_choice, max_full_evals, max_metric_calls] if c is not None]
    if len(chosen) == 0:
        raise typer.BadParameter(
            "You must specify exactly one of: --auto OR --max-full-evals OR --max-metric-calls."
        )
    if len(chosen) > 1:
        raise typer.BadParameter(
            "Exactly one of --auto, --max-full-evals, --max-metric-calls must be specified (not multiple)."
        )
    # If numeric limit chosen ensure auto_choice cleared
    if (max_full_evals is not None or max_metric_calls is not None) and auto_choice:
        auto_choice = None

    try:
        import dspy  # type: ignore  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise typer.Exit(code=1) from exc

    # Use centralized DSPy manager (aligns with agent-framework patterns)
    from ...utils.dspy_manager import configure_dspy_settings  # type: ignore

    configure_dspy_settings(model=effective_model, enable_cache=True)

    supervisor = DSPySupervisor()
    supervisor.set_tool_registry(ToolRegistry())

    reflection_model_value = reflection_model or effective_model
    gepa_options = {
        "auto": auto_choice,
        "max_full_evals": max_full_evals,
        "max_metric_calls": max_metric_calls,
        "reflection_model": reflection_model_value,
        "log_dir": str(log_dir),
        "perfect_score": 1.0,
        "use_history_examples": use_history,
        "history_min_quality": history_min_quality,
        "history_limit": history_limit,
        "val_split": val_split,
        "seed": seed,
    }

    with Progress() as progress:
        task_id = progress.add_task("[cyan]Optimizing with GEPA...", start=False)
        progress.start_task(task_id)

        compiled = compile_supervisor(
            supervisor,
            examples_path=str(examples),
            use_cache=not no_cache,
            optimizer="gepa",
            gepa_options=gepa_options,
        )

        progress.update(task_id, completed=100)
    compiled_name = compiled.__class__.__name__ if compiled else "DSPySupervisor"

    console.print(
        Panel(
            "[green]GEPA optimization complete![/green]\n"
            f"Cache: logs/compiled_supervisor.pkl\n"
            f"Log dir: {log_dir}\n"
            f"Optimizer model: {effective_model}\n"
            f"Compiled module: {compiled_name}",
            title="Success",
            border_style="green",
        )
    )
