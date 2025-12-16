import json
import logging
from pathlib import Path
import yaml
from dotenv import load_dotenv
from agentic_fleet.dspy_modules.lifecycle import configure_dspy_settings
from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
from agentic_fleet.dspy_modules.reasoner_utils import get_reasoner_source_hash
from agentic_fleet.utils.gepa_optimizer import (
    optimize_with_gepa,
    prepare_gepa_datasets,
)
from agentic_fleet.utils.logger import setup_logger

logger: logging.Logger = setup_logger("optimize_reasoner")


def load_config() -> dict:
    """
    Load optimization configuration from src/agentic_fleet/config/workflow_config.yaml.

    Returns:
        dict: Configuration dictionary with DSPy and GEPA settings.

    Raises:
        FileNotFoundError: If config file is not found.
        KeyError: If required configuration keys are missing.
        ValueError: If paths don't exist or are invalid.
    """
    config_path = Path(__file__).parents[1] / "src/agentic_fleet/config/workflow_config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")

    logger.info(f"Loading configuration from {config_path}")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError("Configuration file is empty")

    return config


def validate_and_resolve_paths(base_path: Path, *path_specs: str | None) -> list[Path]:
    """
    Validate and resolve file/directory paths relative to base_path.

    Args:
        base_path: Base directory for resolving relative paths.
        *path_specs: Path strings (may be relative or absolute).

    Returns:
        list[Path]: Resolved Path objects.

    Raises:
        ValueError: If a path doesn't exist or is None/empty.
    """
    resolved = []
    for spec in path_specs:
        if not spec:
            raise ValueError("Path specification is empty or None")

        path = Path(spec) if Path(spec).is_absolute() else base_path / spec

        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")

        resolved.append(path)

    return resolved


def main() -> None:
    """
    Optimize the DSPyReasoner using GEPA optimization.

    Loads configuration from workflow_config.yaml, prepares train/validation
    splits from the golden dataset, initializes the reasoner with enhanced
    signatures, runs GEPA optimization, and saves the compiled module to disk.

    Configuration keys used (from dspy.optimization section):
    - Required: model (from dspy.model), gepa_max_metric_calls
    - Dataset: examples_path (golden dataset for training)
    - GEPA params: gepa_val_split, gepa_seed, gepa_perfect_score, gepa_log_dir,
                   gepa_reflection_model
    - Output: compiled_reasoner_path (from dspy.compiled_reasoner_path)

    Defaults:
    - val_split: 0.2 if not specified
    - seed: 42 if not specified
    - perfect_score: 1.0 if not specified
    """
    # Load environment variables
    load_dotenv()

    # Load configuration from YAML
    config = load_config()
    base_path = Path(__file__).parents[1]

    dspy_config = config.get("dspy", {})
    opt_config = dspy_config.get("optimization", {})

    # Extract required settings
    model = dspy_config.get("model")
    if not model:
        raise ValueError("Missing required config key: dspy.model")

    dataset_path_str = opt_config.get("examples_path")
    if not dataset_path_str:
        raise ValueError("Missing required config key: dspy.optimization.examples_path")

    # Validate and resolve paths
    (dataset_path,) = validate_and_resolve_paths(base_path, dataset_path_str)

    output_path = Path(
        dspy_config.get("compiled_reasoner_path", ".var/cache/dspy/compiled_reasoner.json")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract GEPA optimization parameters with sensible defaults
    val_split = opt_config.get("gepa_val_split", 0.2)
    seed = opt_config.get("gepa_seed", 42)
    max_metric_calls = opt_config.get("gepa_max_metric_calls", 30)
    perfect_score = opt_config.get("gepa_perfect_score", 1.0)
    log_dir = opt_config.get("gepa_log_dir", ".var/logs/dspy/gepa")
    reflection_model = opt_config.get("gepa_reflection_model", model)  # Fall back to main model

    logger.info(f"Configuration loaded: model={model}, dataset={dataset_path}")
    logger.info(
        f"GEPA params: val_split={val_split}, seed={seed}, max_metric_calls={max_metric_calls}"
    )

    # Configure DSPy global settings (uses OPENAI_API_KEY from .env)
    configure_dspy_settings(model=model)

    logger.info(f"Loading dataset from {dataset_path}")
    with open(dataset_path) as f:
        raw_data = json.load(f)

    # Prepare datasets
    trainset, valset = prepare_gepa_datasets(
        base_examples_path=str(dataset_path),
        base_records=raw_data,
        val_split=val_split,
        seed=seed,
    )

    logger.info(f"Training examples: {len(trainset)}")
    logger.info(f"Validation examples: {len(valset)}")

    # Initialize Reasoner (The Student)
    # We use enhanced signatures to match the Golden Dataset structure
    reasoner = DSPyReasoner(use_enhanced_signatures=True)
    reasoner._ensure_modules_initialized()

    # Run GEPA Optimization
    logger.info("Starting GEPA optimization...")
    compiled_reasoner = optimize_with_gepa(
        module=reasoner,
        trainset=trainset,
        valset=valset,
        auto=None,  # Reset default
        max_full_evals=None,  # Reset default
        max_metric_calls=max_metric_calls,
        perfect_score=perfect_score,
        log_dir=log_dir,
        reflection_model=reflection_model,
    )

    logger.info("Optimization complete.")

    # Save the compiled module
    logger.info(f"Saving compiled module to {output_path}")
    compiled_reasoner.save(str(output_path))

    meta_path = Path(f"{output_path}.meta")
    meta_path.write_text(
        json.dumps(
            {
                "version": 1,
                "reasoner_source_hash": get_reasoner_source_hash(),
            },
            indent=2,
        )
    )
    logger.info("Done.")


if __name__ == "__main__":
    main()
