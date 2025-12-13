import json
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parents[1] / "src"))

from dotenv import load_dotenv

from agentic_fleet.dspy_modules.reasoner import (
    DSPyReasoner,
    get_configured_compiled_reasoner_path,
)
from agentic_fleet.dspy_modules.reasoner_utils import get_reasoner_source_hash
from agentic_fleet.utils.dspy_manager import configure_dspy_settings
from agentic_fleet.utils.gepa_optimizer import (
    optimize_with_gepa,
    prepare_gepa_datasets,
)
from agentic_fleet.utils.logger import setup_logger

logger = setup_logger("optimize_reasoner")


def main() -> None:
    """
    Optimize the DSPyReasoner using GEPA optimization.

    Loads the golden dataset, prepares train/validation splits, initializes
    the reasoner with enhanced signatures, runs GEPA optimization, and saves
    the compiled module to disk.
    """
    # Load environment variables
    # Load environment variables
    load_dotenv()

    # Configure DSPy global settings (uses OPENAI_API_KEY from .env)
    configure_dspy_settings(model="gpt-4.1-mini")

    # Configuration
    dataset_path = Path("src/agentic_fleet/data/golden_dataset.json")
    output_path = get_configured_compiled_reasoner_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not dataset_path.exists():
        logger.error(f"Dataset not found at {dataset_path}")
        return

    logger.info(f"Loading dataset from {dataset_path}")
    with open(dataset_path) as f:
        raw_data = json.load(f)

    # Prepare datasets
    trainset, valset = prepare_gepa_datasets(
        base_examples_path=str(dataset_path), base_records=raw_data, val_split=0.2, seed=42
    )

    logger.info(f"Training examples: {len(trainset)}")
    logger.info(f"Validation examples: {len(valset)}")

    # Initialize Reasoner (The Student)
    # We use enhanced signatures to match the Golden Dataset structure
    reasoner = DSPyReasoner(use_enhanced_signatures=True)
    reasoner._ensure_modules_initialized()

    # Configure DSPy (Mock or Real)
    # For GEPA to work, we need a real LM or a very sophisticated mock.
    # Assuming environment variables (OPENAI_API_KEY, etc.) are set for the user.
    # If not, this might fail or fallback to a dummy.
    # We will assume the user has the environment set up as per previous context.

    # Run GEPA Optimization
    logger.info("Starting GEPA optimization...")
    compiled_reasoner = optimize_with_gepa(
        module=reasoner,
        trainset=trainset,
        valset=valset,
        auto=None,  # Reset default
        max_full_evals=None,  # Reset default
        max_metric_calls=30,
        perfect_score=1.0,
        log_dir=".var/logs/gepa_reasoner",
        reflection_model="gpt-4.1-mini",  # or whatever is available/configured
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
