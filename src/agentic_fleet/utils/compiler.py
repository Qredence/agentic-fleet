"""
DSPy compilation utilities for optimizing modules.
Simplified to rely on native DSPy persistence.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dspy.teleprompt import BootstrapFewShot

from agentic_fleet.dspy_modules.gepa.optimizer import (
    convert_to_dspy_examples,
    harvest_history_examples,
    optimize_with_gepa,
    prepare_gepa_datasets,
)

from .progress import NullProgressCallback, ProgressCallback

logger = logging.getLogger(__name__)


def compile_reasoner(
    module: Any,
    examples_path: str = "src/agentic_fleet/data/supervisor_examples.json",
    use_cache: bool = True,
    optimizer: str = "bootstrap",
    gepa_options: dict[str, Any] | None = None,
    dspy_model: str | None = None,
    agent_config: dict[str, Any] | None = None,
    progress_callback: ProgressCallback | None = None,
    allow_gepa_optimization: bool = True,
) -> Any:
    """Compile DSPy reasoner module."""
    if progress_callback is None:
        progress_callback = NullProgressCallback()

    optimizer = optimizer or "bootstrap"
    cache_path = ".var/cache/dspy/compiled_reasoner.json"

    progress_callback.on_start(f"Compiling DSPy reasoner with {optimizer} optimizer")

    if use_cache and os.path.exists(cache_path):
        try:
            progress_callback.on_progress(f"Loading cached module from {cache_path}...")
            module.load(cache_path)
            progress_callback.on_complete(f"Using cached compiled module ({optimizer})")
            logger.info(f"✓ Using cached compiled module from {cache_path}")
            return module
        except Exception as exc:
            logger.warning(f"Failed to load cache, recompiling: {exc}")

    if not os.path.exists(examples_path):
        progress_callback.on_error(f"No training data found at {examples_path}")
        return module

    progress_callback.on_progress(f"Loading training examples from {examples_path}...")
    try:
        with open(examples_path) as f:
            data = json.load(f)
    except Exception as exc:
        progress_callback.on_error("Failed to load training data", exc)
        return module

    if optimizer == "gepa" and allow_gepa_optimization:
        gepa_options = gepa_options or {}
        extra_examples: list[dict[str, Any]] = list(gepa_options.get("extra_examples", []))

        if gepa_options.get("use_history_examples"):
            progress_callback.on_progress("Harvesting history examples...")
            history_examples = harvest_history_examples(
                min_quality=gepa_options.get("history_min_quality", 8.0),
                limit=gepa_options.get("history_limit", 200),
            )
            if history_examples:
                extra_examples.extend(history_examples)
                progress_callback.on_progress(f"Appended {len(history_examples)} history examples")

        progress_callback.on_progress("Preparing GEPA datasets...")
        trainset, valset = prepare_gepa_datasets(
            base_examples_path=examples_path,
            base_records=data,
            extra_examples=extra_examples,
            val_split=gepa_options.get("val_split", 0.2),
            seed=gepa_options.get("seed", 13),
        )

        progress_callback.on_progress("Running GEPA optimization...")
        compiled = optimize_with_gepa(
            module,
            trainset,
            valset,
            auto=gepa_options.get("auto", "light"),
            max_full_evals=gepa_options.get("max_full_evals"),
            max_metric_calls=gepa_options.get("max_metric_calls"),
            reflection_model=gepa_options.get("reflection_model"),
            perfect_score=gepa_options.get("perfect_score", 1.0),
            log_dir=gepa_options.get("log_dir", ".var/logs/gepa"),
            progress_callback=progress_callback,
        )
        progress_callback.on_complete("GEPA optimization complete")

    else:
        # Bootstrap Fallback
        progress_callback.on_progress("Running Bootstrap optimization...")
        trainset = convert_to_dspy_examples(data)

        def routing_metric(example, prediction, trace=None):
            pred_agents = getattr(prediction, "assigned_to", "")
            if isinstance(pred_agents, str):
                pred_agents = [x.strip() for x in pred_agents.split(",")]
            gold_agents = getattr(example, "assigned_to", "")
            if isinstance(gold_agents, str):
                gold_agents = [x.strip() for x in gold_agents.split(",")]

            intersection = len(set(pred_agents) & set(gold_agents))
            union = len(set(pred_agents) | set(gold_agents))
            agent_score = intersection / union if union else 0.0

            mode_match = getattr(prediction, "execution_mode", "") == getattr(
                example, "execution_mode", ""
            )
            return (agent_score * 0.7) + (float(mode_match) * 0.3)

        max_demos = 4
        optimizer_instance = BootstrapFewShot(
            metric=routing_metric,
            max_bootstrapped_demos=max_demos,
            max_labeled_demos=max_demos,
        )
        compiled = optimizer_instance.compile(module, trainset=trainset)
        progress_callback.on_complete("Bootstrap optimization complete")

    if use_cache:
        progress_callback.on_progress(f"Saving to {cache_path}...")
        try:
            compiled.save(cache_path)
            logger.info("✓ Saved compiled module")
        except Exception as exc:
            logger.warning(f"Failed to save module: {exc}")

    return compiled


def compile_answer_quality(
    module: Any = None,
    examples_path: str = "src/agentic_fleet/data/quality_examples.json",
    use_cache: bool = True,
    optimizer: str = "bootstrap",
    progress_callback: ProgressCallback | None = None,
) -> Any:
    """Compile quality assessment module (Simplified stub)."""
    if module is None:
        logger.warning("No module provided for answer quality compilation; skipping.")
        if progress_callback:
            progress_callback.on_error("No module provided for answer quality compilation")
        return None
    if progress_callback:
        progress_callback.on_start("Compiling Answer Quality Module")
        progress_callback.on_complete("Skipping detailed compilation for simplified mode")
    return module


def compile_nlu(
    module: Any = None,
    examples_path: str = "src/agentic_fleet/data/nlu_examples.json",
    use_cache: bool = True,
    optimizer: str = "bootstrap",
    progress_callback: ProgressCallback | None = None,
) -> Any:
    """Compile NLU module (Simplified stub)."""
    if module is None:
        logger.warning("No module provided for NLU compilation; skipping.")
        if progress_callback:
            progress_callback.on_error("No module provided for NLU compilation")
        return None
    if progress_callback:
        progress_callback.on_start("Compiling NLU Module")
        progress_callback.on_complete("Skipping detailed compilation for simplified mode")
    return module


def clear_cache() -> None:
    """Clear compiled module cache (Helper for API)."""
    # Since we now rely on dspy native saving/loading or manual file management,
    # this acts as a no-op or could delete the known cache files if needed.
    pass


def get_cache_info() -> dict[str, Any]:
    """Get cache statistics (Helper for API)."""
    return {"enabled": True, "size": 0, "items": 0, "location": "native_dspy_cache"}


def load_compiled_module(path: str) -> Any | None:
    """Load a compiled DSPy module from a JSON path.

    This function attempts to determine the module type from the filename
    and instantiates the appropriate class before loading weights.
    """
    if not os.path.exists(path):
        logger.warning(f"Compiled artifact not found at {path}")
        return None

    filename = os.path.basename(path).lower()

    # Import modules lazily to avoid circular imports
    try:
        if "routing" in filename:
            from agentic_fleet.dspy_modules.decisions.routing import RoutingDecisionModule

            module = RoutingDecisionModule()
        elif "tool_planning" in filename:
            from agentic_fleet.dspy_modules.decisions.tool_planning import (
                ToolPlanningModule,
            )

            module = ToolPlanningModule()
        elif "quality" in filename or "answer_quality" in filename:
            from agentic_fleet.dspy_modules.decisions.quality import QualityDecisionModule

            module = QualityDecisionModule()
        elif "reasoner" in filename:
            from agentic_fleet.dspy_modules.reasoner import DSPyReasoner

            module = DSPyReasoner()
        else:
            logger.error(f"Unknown module type for path: {path}")
            return None

        # Load weights using DSPy native load
        if path.endswith(".pkl"):
            module.load(path, allow_pickle=True)
        else:
            module.load(path)
        return module

    except Exception as e:
        logger.error(f"Failed to load compiled module from {path}: {e}", exc_info=True)
        return None
