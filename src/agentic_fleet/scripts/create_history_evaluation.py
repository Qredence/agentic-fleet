#!/usr/bin/env python3
"""
Extract evaluation tasks from execution_history.jsonl
Creates test cases for evaluating workflow quality across historical runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_history(history_path: Path) -> list[dict[str, Any]]:
    """Load execution history from JSONL."""
    records = []
    with open(history_path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def extract_evaluation_tasks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert history records to evaluation task format."""
    tasks = []

    for idx, record in enumerate(records, 1):
        task = record.get("task", "").strip()
        result = record.get("result", "").strip()
        quality = record.get("quality", {})

        # Skip invalid/incomplete entries
        if not task or not result:
            continue

        # Extract expected quality metrics
        eval_task = {
            "task": task,
            "expected_output": result,
            "expected_quality_score": quality.get("score", 0.0),
            "expected_keywords": extract_keywords(task),
            "metadata": {
                "history_index": idx,
                "execution_time": record.get("total_time_seconds", 0),
                "complexity": record.get("dspy_analysis", {}).get("complexity", "unknown"),
                "routing_mode": record.get("routing", {}).get("mode", "unknown"),
            },
        }

        tasks.append(eval_task)

    return tasks


def extract_keywords(task: str) -> list[str]:
    """Extract relevant keywords from task description."""
    keywords = set()

    # Common topic keywords
    topic_map = {
        "quantum": ["quantum", "qubit", "superposition", "entanglement"],
        "physic": ["physics", "wave", "particle", "quantum"],
        "computing": ["computing", "computer", "algorithm", "qiskit"],
        "palestinian": ["palestinian", "israel", "occupation", "rights"],
        "tracing": ["tracing", "agent", "multi-agent", "observability"],
        "distance": ["distance", "earth", "sun", "astronomical"],
        "defend": ["defend", "defense", "law", "rights"],
    }

    task_lower = task.lower()
    for key, words in topic_map.items():
        if key in task_lower:
            keywords.update(words)

    return sorted(keywords)


def main() -> None:
    """Run the evaluation task extraction."""
    # Paths
    workspace_root = Path(__file__).parent.parent
    history_path = workspace_root / "logs" / "execution_history.jsonl"
    output_path = workspace_root / "data" / "history_evaluation_tasks.jsonl"

    print(f"Loading execution history from: {history_path}")
    records = load_history(history_path)
    print(f"Loaded {len(records)} historical execution records")

    print("Extracting evaluation tasks...")
    eval_tasks = extract_evaluation_tasks(records)
    print(f"Created {len(eval_tasks)} evaluation tasks")

    # Write evaluation tasks
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for task in eval_tasks:
            f.write(json.dumps(task) + "\n")

    print(f"✓ Evaluation dataset saved to: {output_path}")

    # Print summary
    print("\n--- Dataset Summary ---")
    complexity_counts: dict[str, int] = {}
    for task in eval_tasks:
        complexity = task["metadata"]["complexity"]
        complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1

    print("Tasks by complexity:")
    for complexity, count in sorted(complexity_counts.items()):
        print(f"  {complexity}: {count}")

    if not eval_tasks:
        print("⚠ No valid evaluation tasks extracted. Check execution_history.jsonl format.")
        return

    print(
        f"\nAverage expected quality score: {
            sum(t['expected_quality_score'] for t in eval_tasks) / len(eval_tasks):.2f}"
    )
    print(f"Total unique tasks: {len({t['task'] for t in eval_tasks})}")


if __name__ == "__main__":
    main()
