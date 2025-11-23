"""Evaluation runner for batch task assessment.

The Evaluator loads tasks from a dataset file, executes workflow runs, and computes
configured metrics, writing a structured JSONL report.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .metrics import compute_metrics

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Container for single-task evaluation results."""

    task_id: str
    metrics: dict[str, Any]
    raw: dict[str, Any]


class Evaluator:
    """
    Orchestrates batch evaluation of tasks against a workflow.

    Loads tasks from a dataset, executes them, computes metrics, and generates
    detailed reports and summaries.
    """

    def __init__(
        self,
        workflow_factory,
        dataset_path: str,
        output_dir: str,
        metrics: list[str],
        max_tasks: int = 0,
        stop_on_failure: bool = False,
    ) -> None:
        """
        Initialize the evaluator.

        Args:
            workflow_factory: Async callable returning an initialized workflow
            dataset_path: Path to input dataset (JSON or JSONL)
            output_dir: Directory for output reports
            metrics: List of metric names to compute
            max_tasks: Maximum number of tasks to process (0 for all)
            stop_on_failure: Whether to stop on first metric failure
        """
        self.workflow_factory = workflow_factory  # callable returning initialized workflow
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.metrics = metrics
        self.max_tasks = max_tasks
        self.stop_on_failure = stop_on_failure
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_tasks(self) -> list[dict[str, Any]]:
        """Load tasks from the dataset file."""
        if not self.dataset_path.exists():
            return []
        tasks: list[dict[str, Any]] = []
        if self.dataset_path.suffix == ".jsonl":
            with self.dataset_path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        tasks.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping malformed JSONL line: {line[:100]}")
                        continue
        else:
            try:
                data = json.loads(self.dataset_path.read_text())
                if isinstance(data, list):
                    tasks = [t for t in data if isinstance(t, dict)]
            except Exception as e:
                logger.error(f"Failed to load dataset {self.dataset_path}: {e}")
                pass
        if self.max_tasks and len(tasks) > self.max_tasks:
            tasks = tasks[: self.max_tasks]
        return tasks

    def _baseline_path(self) -> Path:
        """Get path to baseline snapshot file."""
        return self.output_dir / "baseline_snapshot.json"

    def _load_baseline(self) -> dict[str, Any]:
        """Load baseline snapshot if it exists."""
        path = self._baseline_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _compute_output_hash(self, text: str) -> str:
        """Compute SHA256 hash of output text for drift detection."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def run(self) -> dict[str, Any]:
        """
        Execute the evaluation run.

        Returns:
            Summary dictionary containing aggregate metrics
        """
        tasks = self._load_tasks()
        results: list[EvaluationResult] = []
        workflow = await self.workflow_factory()

        baseline = self._load_baseline()
        baseline_hashes = baseline.get("hashes", {}) if baseline else {}
        first_run = not baseline_hashes

        report_path = self.output_dir / "evaluation_report.jsonl"
        with report_path.open("w") as report_file:
            for idx, task in enumerate(tasks, start=1):
                message = task.get("message") or task.get("task") or ""
                if not message:
                    continue
                result = await workflow.run(message)
                metadata = result.get("metadata", {})
                # Provide result text for keyword metric
                task["_result_text"] = str(result.get("result", ""))
                output_text = task["_result_text"]
                output_hash = self._compute_output_hash(output_text)
                # Drift metric: 0 if identical to baseline hash for task id, 1 if
                # different, None if baseline missing
                if "output_drift" not in self.metrics:
                    # allow on-the-fly use even if not configured
                    self.metrics.append("output_drift")
                drift_value = None
                task_id_effective = str(task.get("id", idx))
                if task_id_effective in baseline_hashes:
                    drift_value = 0 if baseline_hashes[task_id_effective] == output_hash else 1
                elif not first_run:
                    drift_value = None
                metric_values = compute_metrics(task, metadata, self.metrics)
                if "output_drift" in self.metrics:
                    metric_values["output_drift"] = drift_value
                eval_result = EvaluationResult(
                    task_id=str(task.get("id", idx)), metrics=metric_values, raw=result
                )
                results.append(eval_result)
                report_line = {
                    "task_id": eval_result.task_id,
                    "message": message,
                    "metrics": eval_result.metrics,
                    "hash": output_hash,
                }
                report_file.write(json.dumps(report_line) + "\n")

                if self.stop_on_failure and any(
                    v in (0, None) for k, v in eval_result.metrics.items() if k.endswith("success")
                ):
                    break

        summary = self._summarize(results)
        summary_path = self.output_dir / "evaluation_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))

        # Write baseline snapshot if first run (hashes only)
        if first_run:
            snapshot = {
                "total_tasks": len(results),
                "hashes": {
                    r.task_id: self._compute_output_hash(r.raw.get("result", "")) for r in results
                },
            }
            self._baseline_path().write_text(json.dumps(snapshot, indent=2))
        return summary

    def _summarize(self, results: list[EvaluationResult]) -> dict[str, Any]:
        """Compute aggregate statistics from individual results."""
        if not results:
            return {"total_tasks": 0, "metrics": {}}
        aggregate: dict[str, list[float]] = {}
        for r in results:
            for k, v in r.metrics.items():
                if isinstance(v, int | float):
                    aggregate.setdefault(k, []).append(float(v))
        metrics_summary = {
            k: {
                "count": len(vals),
                "mean": (sum(vals) / len(vals)) if vals else None,
                "min": min(vals) if vals else None,
                "max": max(vals) if vals else None,
            }
            for k, vals in aggregate.items()
        }
        return {"total_tasks": len(results), "metrics": metrics_summary}
