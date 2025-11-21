import pytest

from agentic_fleet.evaluation.metrics import (
    compute_metrics,
    metric_estimated_cost_usd,
    metric_relevance_score,
    metric_token_count,
)


def test_relevance_score_full_match():
    task = {"keywords": ["alpha", "beta"], "_result_text": "Alpha and beta are here."}
    assert metric_relevance_score(task, {}) == 1.0


def test_relevance_score_partial_match():
    task = {
        "keywords": ["alpha", "beta", "gamma"],
        "_result_text": "Beta and alpha only.",
    }
    assert pytest.approx(metric_relevance_score(task, {}), 1e-6) == 2 / 3


def test_relevance_score_no_keywords():
    task = {"_result_text": "Nothing"}
    assert metric_relevance_score(task, {}) is None


def test_token_count_basic():
    task = {"_result_text": "Hello world!"}
    count = metric_token_count(task, {})
    # "Hello", "world", "!" => 3 tokens
    assert count == 3


def test_estimated_cost_rounded():
    task = {"_result_text": "One two three four five six seven eight nine ten"}
    count = metric_token_count(task, {})
    cost = metric_estimated_cost_usd(task, {})
    assert count is not None
    assert count > 0
    assert cost is not None
    # Cost should be proportional to count and small
    assert cost < 0.01


def test_compute_metrics_integration():
    task = {"keywords": ["x"], "_result_text": "x y z"}
    meta = {}
    metrics = compute_metrics(
        task,
        meta,
        ["relevance_score", "token_count", "estimated_cost_usd", "nonexistent"],
    )
    assert "relevance_score" in metrics
    assert "token_count" in metrics
    assert "estimated_cost_usd" in metrics
    assert metrics["nonexistent"] is None
