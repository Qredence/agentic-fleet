#!/usr/bin/env python3
"""
Script to retroactively evaluate execution history and assign quality scores.
"""

import json
from pathlib import Path

from agentic_fleet.dspy_modules.lifecycle import configure_dspy_settings
from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
from agentic_fleet.utils.history_manager import HistoryManager
from agentic_fleet.utils.logger import setup_logger

logger = setup_logger(__name__)


def evaluate_history(limit: int = 100):
    """Evaluate recent history items that lack quality scores."""

    # Configure DSPy
    configure_dspy_settings(model="gpt-4.1", enable_cache=True)

    reasoner = DSPyReasoner()
    history_manager = HistoryManager()

    executions = history_manager.load_history(limit=limit)
    updated_count = 0

    print(f"Loaded {len(executions)} executions. Checking for missing scores...")

    updated_executions = []

    for execution in executions:
        quality = execution.get("quality", {})
        score = quality.get("score", 0.0)

        # If score is 0 or missing, evaluate it
        if score == 0.0:
            task = execution.get("task", "")
            result = execution.get("result", "")

            if task and result:
                print(f"Evaluating task: {task[:50]}...")
                try:
                    assessment = reasoner.assess_quality(task=task, result=result)
                    new_score = assessment.get("score", 0.0)

                    execution["quality"] = {
                        "score": new_score,
                        "missing": assessment.get("missing", ""),
                        "improvements": assessment.get("improvements", ""),
                        "reasoning": assessment.get("reasoning", ""),
                        "evaluated_at": "retroactive",
                    }
                    updated_count += 1
                    print(f"  -> Score: {new_score}/10")
                except Exception as e:
                    print(f"  -> Failed to evaluate: {e}")

        updated_executions.append(execution)

    if updated_count > 0:
        print(f"Updating {updated_count} executions in history file...")
        # We need to write back to the file. HistoryManager doesn't have a bulk update method exposed easily,
        # so we'll write directly to the file for this script.

        jsonl_path = Path(".var/logs/execution_history.jsonl")
        if jsonl_path.exists():
            # Backup first
            backup_path = jsonl_path.with_suffix(".jsonl.bak")
            with open(jsonl_path, "rb") as src, open(backup_path, "wb") as dst:
                dst.write(src.read())

            with open(jsonl_path, "w") as f:
                for ex in updated_executions:
                    f.write(json.dumps(ex) + "\n")
            print(f"Saved updated history to {jsonl_path}")
        else:
            print("History file not found (unexpected)")
    else:
        print("No executions needed evaluation.")


if __name__ == "__main__":
    evaluate_history()
