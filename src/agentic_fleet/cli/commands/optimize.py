"""Optimize command for GEPA optimization."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

from ...dspy_modules.reasoner import DSPyReasoner
from ...utils.cfg import (
    DEFAULT_ANSWER_QUALITY_CACHE_PATH,
    DEFAULT_CACHE_PATH,
    DEFAULT_GEPA_LOG_DIR,
    DEFAULT_NLU_CACHE_PATH,
    load_config,
)
from ...utils.compiler import compile_answer_quality, compile_nlu, compile_reasoner
from ..utils import init_tracing, resolve_resource_path

console = Console()


def gepa_optimize(
    examples: Annotated[
        Path,
        typer.Option("--examples", "-e", help="Training dataset path"),
    ] = Path("data/supervisor_examples.json"),
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Model for DSPy LM (defaults to config dspy.model)"),
    ] = None,
    auto: Annotated[
        str | None,
        typer.Option(
            "--auto",
            help=(
                "GEPA auto configuration (light|medium|heavy). Mutually exclusive with --max-full-evals "
                "/ --max-metric-calls. If omitted, you MUST provide one numeric limit."
            ),
            case_sensitive=False,
        ),
    ] = None,
    max_full_evals: Annotated[
        int | None,
        typer.Option(
            "--max-full-evals",
            help="Explicit full GEPA evaluation budget (exclusive with --auto / --max-metric-calls)",
        ),
    ] = None,
    max_metric_calls: Annotated[
        int | None,
        typer.Option(
            "--max-metric-calls",
            help="Explicit metric call budget (exclusive with --auto / --max-full-evals)",
        ),
    ] = None,
    reflection_model: Annotated[
        str | None,
        typer.Option(
            "--reflection-model", help="Optional LM for reflections (defaults to main LM)"
        ),
    ] = None,
    val_split: Annotated[
        float, typer.Option("--val-split", help="Validation split (0.0-0.5)")
    ] = 0.2,
    use_history: Annotated[
        bool,
        typer.Option(
            "--use-history/--no-history",
            help="Augment training data with high-quality execution history",
        ),
    ] = False,
    history_min_quality: Annotated[
        float,
        typer.Option("--history-min-quality", help="Minimum quality score for harvested history"),
    ] = 8.0,
    history_limit: Annotated[
        int, typer.Option("--history-limit", help="History lookback size")
    ] = 200,
    log_dir: Annotated[Path, typer.Option("--log-dir", help="Directory for GEPA logs")] = Path(
        DEFAULT_GEPA_LOG_DIR
    ),
    seed: Annotated[int, typer.Option("--seed", help="Random seed for dataset shuffle")] = 13,
    no_cache: Annotated[
        bool,
        typer.Option(
            "--no-cache", help="Do not read/write compiled module cache (always recompile)"
        ),
    ] = False,
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
    from ...dspy_modules.lifecycle import configure_dspy_settings

    configure_dspy_settings(model=effective_model, enable_cache=True)

    supervisor = DSPyReasoner()

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

        compiled = compile_reasoner(
            supervisor,
            examples_path=str(examples),
            use_cache=not no_cache,
            optimizer="gepa",
            gepa_options=gepa_options,
        )

        progress.update(task_id, completed=100)

    # Also compile AnswerQualityModule for offline quality scoring
    with Progress() as progress:
        task_id = progress.add_task("[cyan]Compiling AnswerQualityModule...", start=False)
        progress.start_task(task_id)

        compile_answer_quality(use_cache=not no_cache)

        progress.update(task_id, completed=100)

    # Compile DSPyNLU module
    with Progress() as progress:
        task_id = progress.add_task("[cyan]Compiling DSPyNLU...", start=False)
        progress.start_task(task_id)

        compile_nlu(use_cache=not no_cache)

        progress.update(task_id, completed=100)

    compiled_name = compiled.__class__.__name__ if compiled else "DSPyReasoner"

    console.print(
        Panel(
            "[green]GEPA optimization complete![/green]\n"
            f"Supervisor cache: {DEFAULT_CACHE_PATH}\n"
            f"AnswerQuality cache: {DEFAULT_ANSWER_QUALITY_CACHE_PATH}\n"
            f"NLU cache: {DEFAULT_NLU_CACHE_PATH}\n"
            f"Log dir: {log_dir}\n"
            f"Optimizer model: {effective_model}\n"
            f"Compiled module: {compiled_name}",
            title="Success",
            border_style="green",
        )
    )
