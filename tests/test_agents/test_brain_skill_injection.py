"""Tests for FleetBrain skill/context injection."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import agentic_fleet.agents.base as base_module
import agentic_fleet.middleware.context as context_module
from agentic_fleet.dspy_modules.signatures import PlannerSignature, TaskContext, WorkerSignature
from agentic_fleet.middleware.context import ContextModulator
from agentic_fleet.skills.models import Skill, SkillContent, SkillMetadata


class FakeCoT:
    def __init__(self, signature):
        self.signature = signature
        self.last_kwargs = None

    def __call__(self, **kwargs):
        self.last_kwargs = kwargs
        return {"ok": True}


@pytest.mark.asyncio
async def test_planner_injects_context_and_available_skills(monkeypatch):
    monkeypatch.setattr(base_module.dspy, "ChainOfThought", FakeCoT)
    skill = Skill(
        metadata=SkillMetadata(
            skill_id="web-research",
            name="Web Research",
            version="1.0.0",
            description="Test",
            team_id="research",
            tags=["test"],
        ),
        content=SkillContent(
            purpose="Test",
            when_to_use="Test",
            how_to_apply="Test",
            example="Test",
        ),
    )
    monkeypatch.setattr(context_module, "load_team_skills", lambda _: [skill])

    async with ContextModulator.scope("research"):
        ContextModulator.mount_skill("web-research")
        brain = base_module.FleetBrain(PlannerSignature)
        brain(task="Test")

        kwargs = brain.program.last_kwargs
        assert isinstance(kwargs["context"], TaskContext)
        assert kwargs["context"].mounted_skills == ["web-research"]
        assert kwargs["available_skills"] == "web-research"


@pytest.mark.asyncio
async def test_worker_injects_mounted_skills(monkeypatch):
    monkeypatch.setattr(base_module.dspy, "ChainOfThought", FakeCoT)
    skill = Skill(
        metadata=SkillMetadata(
            skill_id="web-research",
            name="Web Research",
            version="1.0.0",
            description="Test",
            team_id="research",
            tags=["test"],
        ),
        content=SkillContent(
            purpose="Test",
            when_to_use="Test",
            how_to_apply="Test",
            example="Test",
        ),
    )
    monkeypatch.setattr(context_module, "load_team_skills", lambda _: [skill])

    async with ContextModulator.scope("research"):
        ContextModulator.mount_skill("web-research")
        brain = base_module.FleetBrain(WorkerSignature)
        brain(step="Do work")

        kwargs = brain.program.last_kwargs
        assert kwargs["mounted_skills"] == "web-research"
