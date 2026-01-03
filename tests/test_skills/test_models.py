"""Tests for skill data models."""

import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agentic_fleet.skills.models import (
    Skill,
    SkillContent,
    SkillContext,
    SkillMetadata,
)

def _make_skill(skill_id: str, team_id: str = "research") -> Skill:
    return Skill(
        metadata=SkillMetadata(
            skill_id=skill_id,
            name=skill_id.replace("-", " ").title(),
            version="1.0.0",
            description="Test",
            team_id=team_id,
            tags=["test"],
        ),
        content=SkillContent(
            purpose="Test",
            when_to_use="Test",
            how_to_apply="Test",
            example="Test",
        ),
    )


class TestSkillMetadata:
    """Tests for SkillMetadata model."""

    def test_create_metadata(self):
        """Test creating skill metadata."""
        metadata = SkillMetadata(
            skill_id="web-research",
            name="Web Research",
            version="1.0.0",
            description="Perform web research",
            team_id="research",
            tags=["research", "browser"],
        )
        assert metadata.skill_id == "web-research"
        assert metadata.name == "Web Research"
        assert "research" in metadata.tags

    def test_skill_id_validation(self):
        """Test skill_id format validation."""
        with pytest.raises(ValueError):
            SkillMetadata(
                skill_id="invalid skill id",  # Contains spaces
                name="Test",
                version="1.0.0",
                description="Test",
                team_id="default",
                tags=[],
            )

    def test_skill_id_normalization(self):
        """Test skill_id is normalized to lowercase with dashes."""
        metadata = SkillMetadata(
            skill_id="My_Skill",
            name="Test",
            version="1.0.0",
            description="Test",
            team_id="default",
            tags=[],
        )
        assert metadata.skill_id == "my-skill"

    def test_tags_normalization(self):
        """Test tags are normalized to lowercase."""
        metadata = SkillMetadata(
            skill_id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            team_id="default",
            tags=["Research", "CODING"],
        )
        assert metadata.tags == ["research", "coding"]


class TestSkillContent:
    """Tests for SkillContent model."""

    def test_create_content(self):
        """Test creating skill content."""
        content = SkillContent(
            purpose="Extract web information",
            when_to_use="Need current data",
            how_to_apply="Search and browse",
            example="Research quantum computing",
        )
        assert content.purpose == "Extract web information"
        assert content.when_to_use == "Need current data"

    def test_content_with_constraints(self):
        """Test content with constraints and prerequisites."""
        content = SkillContent(
            purpose="Test",
            when_to_use="Test",
            how_to_apply="Test",
            example="Test",
            constraints=["constraint1", "constraint2"],
            prerequisites=["prereq1"],
        )
        assert len(content.constraints) == 2
        assert len(content.prerequisites) == 1


class TestSkill:
    """Tests for Skill model."""

    def test_skill_from_dict(self):
        """Test creating skill from dictionary."""
        data = {
            "metadata": {
                "skill_id": "test-skill",
                "name": "Test Skill",
                "version": "1.0.0",
                "description": "A test skill",
                "team_id": "default",
                "tags": ["test"],
            },
            "content": {
                "purpose": "Test purpose",
                "when_to_use": "Test when",
                "how_to_apply": "Test how",
                "example": "Test example",
                "constraints": [],
                "prerequisites": [],
            },
        }
        skill = Skill.from_dict(data)
        assert skill.metadata.skill_id == "test-skill"
        assert skill.content.purpose == "Test purpose"

    def test_skill_to_dict(self):
        """Test converting skill to dictionary."""
        skill = Skill(
            metadata=SkillMetadata(
                skill_id="test",
                name="Test",
                version="1.0.0",
                description="Test",
                team_id="default",
                tags=[],
            ),
            content=SkillContent(
                purpose="Test",
                when_to_use="Test",
                how_to_apply="Test",
                example="",
            ),
        )
        data = skill.to_dict()
        assert data["metadata"]["skill_id"] == "test"
        assert data["content"]["purpose"] == "Test"


class TestSkillContext:
    """Tests for SkillContext model."""

    def test_create_context(self):
        """Test creating skill context."""
        ctx = SkillContext(
            team_id="research",
            tools=["browser", "search"],
            mounted_skills=[],
            available_skills=[_make_skill("web-research")],
        )
        assert ctx.team_id == "research"
        assert len(ctx.tools) == 2

    def test_add_skill(self):
        """Test mounting a skill."""
        ctx = SkillContext(
            team_id="research",
            tools=[],
            mounted_skills=[],
            available_skills=[_make_skill("web-research"), _make_skill("data-analysis")],
        )
        assert ctx.has_skill("web-research") is False
        ctx.add_skill("web-research")
        assert ctx.has_skill("web-research") is True
        assert "web-research" in ctx.mounted_skills

    def test_remove_skill(self):
        """Test unmounting a skill."""
        ctx = SkillContext(
            team_id="research",
            tools=[],
            mounted_skills=["web-research"],
            available_skills=[_make_skill("web-research")],
        )
        ctx.remove_skill("web-research")
        assert ctx.has_skill("web-research") is False

    def test_is_available(self):
        """Test checking skill availability."""
        ctx = SkillContext(
            team_id="research",
            tools=[],
            mounted_skills=[],
            available_skills=[_make_skill("web-research")],
        )
        assert ctx.is_available("web-research") is True
        assert ctx.is_available("nonexistent") is False

    def test_add_duplicate_skill(self):
        """Test that adding same skill twice doesn't duplicate."""
        ctx = SkillContext(
            team_id="research",
            tools=[],
            mounted_skills=[],
            available_skills=[_make_skill("web-research")],
        )
        ctx.add_skill("web-research")
        ctx.add_skill("web-research")
        assert len(ctx.mounted_skills) == 1
