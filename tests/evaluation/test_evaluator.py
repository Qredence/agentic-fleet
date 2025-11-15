"""Tests for evaluation framework components."""

from __future__ import annotations

from typing import Any

import pytest

from agentic_fleet.evaluation.evaluator import Evaluator


class FakeWorkflow:
    def __init__(self):
        self.calls = 0

    async def run(self, message: str) -> dict[str, Any]:
        self.calls += 1
        # Provide deterministic metadata; alternate success/partial for keyword coverage
        quality_score = 9.0 if self.calls == 1 else 6.5
        result_text = (
            "Multi-agent workflow benefits include coordination, specialization, and scalability"
            if self.calls == 1
            else "DSPy improves routing but advantages vary"
        )
        metadata = {
            "quality": {
                "score": quality_score,
                "improvements": "" if quality_score >= 8 else "Refine",
            },
            "routing": {
                "mode": "sequential",
                "agents": ["researcher", "writer"],
                "confidence": 0.82,
            },
            "execution_time": 1.23,
        }
        return {"result": result_text, "metadata": metadata}


@pytest.mark.asyncio
async def test_evaluator_runs_and_summarizes(tmp_path):
    # Create dataset file
    dataset_path = tmp_path / "eval.jsonl"
    dataset_path.write_text(
        '{"id": "t1", "message": "Test task one", "keywords": ["multi-agent", "workflow", "benefits"]}\n'
        '{"id": "t2", "message": "Test task two", "keywords": ["DSPy", "routing", "advantages"]}\n'
    )

    async def workflow_factory():
        return FakeWorkflow()

    evaluator = Evaluator(
        workflow_factory=workflow_factory,
        dataset_path=str(dataset_path),
        output_dir=str(tmp_path),
        metrics=[
            "quality_score",
            "keyword_success",
            "latency_seconds",
            "routing_efficiency",
            "refinement_triggered",
        ],
    )

    summary = await evaluator.run()
    assert summary["total_tasks"] == 2
    assert "quality_score" in summary["metrics"]
    assert summary["metrics"]["quality_score"]["count"] == 2
    # Mean between 9.0 and 6.5
    mean_quality = summary["metrics"]["quality_score"]["mean"]
    assert 7.0 < mean_quality < 9.0
    # Keyword success has at least one value (first task success, second fail)
    assert summary["metrics"]["keyword_success"]["count"] == 2
