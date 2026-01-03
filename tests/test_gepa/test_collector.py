"""Unit tests for TraceCollector."""

import sys
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agent_framework import AgentRunEvent, AgentRunResponse

from agentic_fleet import config
from agentic_fleet.gepa.collector import TraceCollector


def _event(executor_id: str, value: dict) -> AgentRunEvent:
    return AgentRunEvent(executor_id, AgentRunResponse(value=value))


def test_extract_examples_captures_skills(reset_team_registry):
    collector = TraceCollector()

    history = [
        _event(
            "Router",
            {
                "original_task": "Evaluate model output",
                "target_team": "research",
            },
        ),
        _event(
            "Planner",
            {
                "plan": "Step one",
                "mounted_skills": "web-research",
                "available_skills": ["web-research", "data-analysis"],
            },
        ),
        _event("Worker", {"result": "Done"}),
        _event("Judge", {"is_approved": True}),
    ]

    examples = collector.extract_examples(history)
    assert len(examples) == 1

    example = examples[0]
    context = example.context

    assert context.team_id == "research"
    assert context.mounted_skills == ["web-research"]
    assert context.available_skills == ["web-research", "data-analysis"]
    assert context.tools == config.TEAM_REGISTRY["research"]["tools"]


def test_extract_examples_missing_available_skills_stays_empty(reset_team_registry):
    collector = TraceCollector()

    history = [
        _event(
            "Router",
            {
                "original_task": "Evaluate model output",
                "target_team": "research",
            },
        ),
        _event(
            "Planner",
            {
                "plan": "Step one",
                "mounted_skills": "web-research",
            },
        ),
        _event("Worker", {"result": "Done"}),
        _event("Judge", {"is_approved": True}),
    ]

    examples = collector.extract_examples(history)
    assert len(examples) == 1

    context = examples[0].context
    assert context.available_skills == []


def test_extract_skill_usage_records_mounted_skills(reset_team_registry):
    collector = TraceCollector()

    history = [
        _event(
            "Router",
            {
                "original_task": "Evaluate design tradeoffs",
                "target_team": "research",
                "required_skills": "web-research",
            },
        ),
        _event("Planner", {"mounted_skills": "web-research, data-analysis"}),
        _event("Judge", {"is_approved": "true"}),
    ]

    usages = collector.extract_skill_usage(history)
    assert len(usages) == 2

    for usage in usages:
        assert usage["team_id"] == "research"
        assert usage["was_successful"] is True
        assert usage["task_type"] == "analysis"

    skill_ids = {usage["skill_id"] for usage in usages}
    assert skill_ids == {"web-research", "data-analysis"}
