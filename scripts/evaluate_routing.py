import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parents[1] / "src"))

from agentic_fleet.dspy_modules.lifecycle import configure_dspy_settings
from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
from agentic_fleet.utils.logger import setup_logger

logger = setup_logger("evaluate_routing")


def evaluate_routing() -> None:
    """
    Evaluate routing accuracy against golden dataset.

    Loads examples from golden_dataset.json, runs DSPyReasoner routing,
    compares predictions against ground truth, and generates a Markdown report
    with agent assignment accuracy and execution mode accuracy metrics.

    Report is written to evaluation_report.md.
    """
    load_dotenv()
    configure_dspy_settings(model="gpt-4.1-mini")

    dataset_path = Path("src/agentic_fleet/data/golden_dataset.json")
    if not dataset_path.exists():
        logger.error(f"Dataset not found at {dataset_path}")
        return

    logger.info("Loading golden dataset...")
    with open(dataset_path) as f:
        examples = json.load(f)

    # Initialize Reasoner (Optimized)
    reasoner = DSPyReasoner(use_enhanced_signatures=True)
    reasoner._ensure_modules_initialized()

    # We assume 'compiled_reasoner.json' is automatically loaded by the reasoner
    # if it exists, thanks to our previous changes.

    results = []
    correct_assignments = 0
    correct_modes = 0
    total = len(examples)

    print(f"\nEvaluating {total} examples...\n")

    for i, ex in enumerate(examples):
        task = ex["task"]
        ground_truth_agents = set(ex["assigned_to"])
        ground_truth_mode = ex["mode"]

        # Prepare context
        team_dict = {}  # Mock team from capabilities string if needed,
        # but reasoner.route_task expects a dict.
        # Parse team_capabilities string from example to a dict
        team_caps_str = ex.get("team_capabilities", "")
        # Very rough parsing just to feed the reasoner something if it expects a dict
        # In reality, route_task argument 'team' is dict[str, str]
        # Example str: "- Writer: Creative writing.\n- Researcher: Search."
        for line in team_caps_str.split("\n"):
            if ":" in line:
                name, desc = line.split(":", 1)
                team_dict[name.strip("- ")] = desc.strip()

        # Run Routing
        prediction = reasoner.route_task(
            task=task,
            team=team_dict,
            context=ex.get("context", ""),
            skip_cache=True,  # Ensure we test the model
        )

        predicted_agents = set(prediction["assigned_to"])
        predicted_mode = prediction["mode"]

        # Metrics
        agents_match = ground_truth_agents == predicted_agents
        mode_match = ground_truth_mode == predicted_mode

        if agents_match:
            correct_assignments += 1
        if mode_match:
            correct_modes += 1

        results.append(
            {
                "id": i + 1,
                "task": task[:50] + "...",
                "expected_agents": list(ground_truth_agents),
                "predicted_agents": list(predicted_agents),
                "agents_match": agents_match,
                "expected_mode": ground_truth_mode,
                "predicted_mode": predicted_mode,
                "mode_match": mode_match,
            }
        )

        status = "✅" if (agents_match and mode_match) else "❌"
        print(f"{status} [{i + 1}/{total}] Agents: {predicted_agents} vs {ground_truth_agents}")

    # Calculate Aggregates
    agent_accuracy = (correct_assignments / total) * 100
    mode_accuracy = (correct_modes / total) * 100

    report = f"""# Routing Evaluation Report

**Total Examples**: {total}
**Agent Selection Accuracy**: {agent_accuracy:.1f}%
**Execution Mode Accuracy**: {mode_accuracy:.1f}%

## Detailed Results

| ID | Task | Expected Agents | Predicted Agents | Match | Expected Mode | Predicted Mode | Match |
|----|------|-----------------|------------------|-------|---------------|----------------|-------|
"""
    for res in results:
        report += f"| {res['id']} | {res['task']} | {res['expected_agents']} | {res['predicted_agents']} | {'✅' if res['agents_match'] else '❌'} | {res['expected_mode']} | {res['predicted_mode']} | {'✅' if res['mode_match'] else '❌'} |\n"

    output_path = Path("evaluation_report.md")
    with open(output_path, "w") as f:
        f.write(report)

    logger.info(f"Evaluation complete. Report saved to {output_path}")


if __name__ == "__main__":
    evaluate_routing()
