#!/usr/bin/env python3
"""Evaluate execution_history.jsonl using DSPy with gpt-5-nano.

This script reads the execution history, evaluates each task-result pair
using DSPy's ChainOfThought, and outputs results to evaluation_results.jsonl.

Usage:
    uv run python scripts/evaluate_history.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import dspy

# Project root for relative paths
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_PATH = PROJECT_ROOT / ".var" / "logs" / "execution_history.jsonl"
OUTPUT_PATH = PROJECT_ROOT / ".var" / "logs" / "evaluation_results.jsonl"


class AnswerQuality(dspy.Signature):
    """Evaluate answer quality against the user's task.

    Scoring rubric (1-10):
    - 9-10: Correct, complete, and well-formatted
    - 7-8: Correct with minor omissions or style issues
    - 5-6: Partially correct or incomplete
    - 3-4: Mostly incorrect but shows understanding
    - 1-2: Incorrect, irrelevant, or fails to answer

    For simple factual tasks (math, definitions, yes/no), correctness is paramount.
    A correct short answer should score 9-10.
    """

    question = dspy.InputField(desc="The user's original question or task")
    answer = dspy.InputField(desc="The assistant's response")

    is_correct = dspy.OutputField(
        desc="Is the answer factually/logically correct? (yes/no/partial)"
    )
    is_complete = dspy.OutputField(desc="Does it fully address the task? (yes/no/partial)")
    reasoning = dspy.OutputField(desc="Brief rationale for the score")
    score = dspy.OutputField(desc="Quality score 1-10 (prioritize correctness)")


def setup_dspy() -> None:
    """Configure DSPy with gpt-5-nano model."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    lm = dspy.LM(model="openai/gpt-5-nano", api_key=api_key)
    dspy.settings.configure(lm=lm)
    print("DSPy configured with gpt-5-nano")


def load_examples() -> list[dspy.Example]:
    """Load task-result pairs from execution history."""
    if not INPUT_PATH.exists():
        print(f"Error: Input file not found: {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)

    examples = []
    with INPUT_PATH.open("r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if "task" in row and "result" in row:
                    examples.append(
                        dspy.Example(
                            question=row["task"],
                            answer=row["result"],
                            workflow_id=row.get("workflowId", f"unknown-{line_num}"),
                            existing_score=row.get("quality", {}).get("score"),
                        ).with_inputs("question", "answer")
                    )
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping malformed JSON at line {line_num}: {e}")
                continue

    return examples


def evaluate_examples(examples: list[dspy.Example]) -> list[dict]:
    """Run DSPy evaluation on each example, saving incrementally."""
    evaluator = dspy.ChainOfThought(AnswerQuality)
    results = []

    print(f"\nEvaluating {len(examples)} records with gpt-5-nano...\n")

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Open file for incremental writing
    with OUTPUT_PATH.open("w") as f:
        for i, ex in enumerate(examples, 1):
            try:
                pred = evaluator(question=ex.question, answer=ex.answer)
                score = _parse_score(pred.score)
                result_entry = {
                    "workflow_id": ex.workflow_id,
                    "task": ex.question,
                    "result": ex.answer[:500] + "..." if len(ex.answer) > 500 else ex.answer,
                    "dspy_score": score,
                    "dspy_is_correct": getattr(pred, "is_correct", None),
                    "dspy_is_complete": getattr(pred, "is_complete", None),
                    "dspy_reasoning": pred.reasoning,
                    "existing_score": ex.existing_score,
                }
                results.append(result_entry)
                f.write(json.dumps(result_entry) + "\n")
                f.flush()
                print(
                    f"[{i}/{len(examples)}] Score: {score:.1f} | Correct: {pred.is_correct} | Workflow: {ex.workflow_id}"
                )
            except Exception as e:
                print(f"[{i}/{len(examples)}] Error: {e}")
                error_entry = {
                    "workflow_id": ex.workflow_id,
                    "task": ex.question,
                    "result": ex.answer[:500] + "..." if len(ex.answer) > 500 else ex.answer,
                    "dspy_score": None,
                    "dspy_reasoning": f"Evaluation error: {e}",
                    "existing_score": ex.existing_score,
                }
                results.append(error_entry)
                f.write(json.dumps(error_entry) + "\n")
                f.flush()

    return results


def _parse_score(raw_score) -> float:
    """Parse score value, handling various formats."""
    try:
        if isinstance(raw_score, (int, float)):
            return float(raw_score)
        s = str(raw_score).strip()
        # Handle "8/10" or "8 out of 10" formats
        if "/" in s:
            s = s.split("/")[0].strip()
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def save_results() -> None:
    """Print save confirmation (legacy, results now saved incrementally)."""
    print(f"\nResults saved to {OUTPUT_PATH}")


def print_summary(results: list[dict]) -> None:
    """Print evaluation summary statistics."""
    scores = [r["dspy_score"] for r in results if r["dspy_score"] is not None]
    if not scores:
        print("\nNo valid scores to summarize.")
        return

    avg_score = sum(scores) / len(scores)
    min_score = min(scores)
    max_score = max(scores)

    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Total records evaluated: {len(results)}")
    print(f"Valid scores:            {len(scores)}")
    print(f"Average score:           {avg_score:.2f}/10")
    print(f"Min score:               {min_score:.1f}/10")
    print(f"Max score:               {max_score:.1f}/10")
    print("=" * 50)


def main() -> None:
    """Main entry point."""
    setup_dspy()
    examples = load_examples()

    if not examples:
        print("No valid examples found in the execution history.")
        sys.exit(0)

    results = evaluate_examples(examples)
    save_results()
    print_summary(results)


if __name__ == "__main__":
    main()
