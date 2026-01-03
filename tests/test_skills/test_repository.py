"""Tests for skill repository and file I/O."""

import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agentic_fleet.skills.repository import (
    _parse_skill_file,
    _parse_list_field,
    list_team_skills,
    load_skill,
    skill_exists,
)
from agentic_fleet.skills.models import SkillContext


class TestParseSkillFile:
    """Tests for SKILL.md file parsing."""

    @pytest.fixture
    def sample_skill_file(self, tmp_path):
        """Create a sample skill file for testing."""
        skill_dir = tmp_path / "default" / "test-skill"
        skill_dir.mkdir(parents=True)

        content = """---
skill_id: test-skill
name: Test Skill
version: 1.0.0
description: A test skill
team_id: default
tags: [test, sample]
---
# Purpose
Test purpose description

# When to Use
Test when to use

# How to Apply
Test how to apply

# Example
Test example
"""
        (skill_dir / "SKILL.md").write_text(content)
        return skill_dir / "SKILL.md"

    def test_parse_valid_file(self, sample_skill_file):
        """Test parsing a valid SKILL.md file."""
        skill = _parse_skill_file(sample_skill_file)
        assert skill is not None
        assert skill.metadata.skill_id == "test-skill"
        assert skill.metadata.name == "Test Skill"
        assert "test" in skill.metadata.tags

    def test_parse_invalid_file(self, tmp_path):
        """Test parsing invalid file returns None."""
        invalid_path = tmp_path / "invalid.md"
        invalid_path.write_text("no frontmatter here")
        result = _parse_skill_file(invalid_path)
        assert result is None

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file returns None."""
        empty_path = tmp_path / "empty.md"
        empty_path.write_text("---")
        result = _parse_skill_file(empty_path)
        assert result is None

    def test_content_sections_parsed(self, sample_skill_file):
        """Test that markdown sections are correctly parsed."""
        skill = _parse_skill_file(sample_skill_file)
        assert skill.content.purpose == "Test purpose description"
        assert skill.content.when_to_use == "Test when to use"
        assert skill.content.how_to_apply == "Test how to apply"


class TestParseListField:
    """Tests for list field parsing."""

    def test_empty_string(self):
        """Test parsing empty string."""
        result = _parse_list_field("")
        assert result == []

    def test_comma_separated(self):
        """Test parsing comma-separated values."""
        result = _parse_list_field("one, two, three")
        assert result == ["one", "two", "three"]

    def test_newline_separated(self):
        """Test parsing newline-separated values."""
        result = _parse_list_field("one\ntwo\nthree")
        assert result == ["one", "two", "three"]

    def test_list_input(self):
        """Test that list input is preserved."""
        result = _parse_list_field(["one", "two"])
        assert result == ["one", "two"]


class TestListTeamSkills:
    """Tests for team skill discovery."""

    @pytest.fixture
    def skills_setup(self, tmp_path):
        """Set up test skill directory structure."""
        skills_path = tmp_path / "skills"
        research_dir = skills_path / "research"
        research_dir.mkdir(parents=True)

        # Create web-research skill
        web_research = research_dir / "web-research"
        web_research.mkdir()
        (web_research / "SKILL.md").write_text("""---
skill_id: web-research
name: Web Research
version: 1.0.0
description: Test
team_id: research
tags: [test]
---
# Purpose
Test

# When to Use
Test

# How to Apply
Test

# Example
Test
""")

        # Create code-review skill
        coding_dir = skills_path / "coding"
        coding_dir.mkdir()
        code_review = coding_dir / "code-review"
        code_review.mkdir()
        (code_review / "SKILL.md").write_text("""---
skill_id: code-review
name: Code Review
version: 1.0.0
description: Test
team_id: coding
tags: [test]
---
# Purpose
Test

# When to Use
Test

# How to Apply
Test

# Example
Test
""")

        # Create a skill without SKILL.md (should be ignored)
        incomplete_dir = research_dir / "incomplete"
        incomplete_dir.mkdir()

        return skills_path

    def test_list_team_skills(self, skills_setup, monkeypatch):
        """Test listing skills for a team."""
        import agentic_fleet.skills.repository as repo_module

        monkeypatch.setattr(repo_module, "SKILLS_BASE_PATH", skills_setup)

        skills = list_team_skills("research")
        assert "web-research" in skills
        assert "incomplete" not in skills

    def test_list_skills_across_teams(self, skills_setup, monkeypatch):
        """Test listing skills across all teams."""
        import agentic_fleet.skills.repository as repo_module

        monkeypatch.setattr(repo_module, "SKILLS_BASE_PATH", skills_setup)

        research_skills = list_team_skills("research")
        coding_skills = list_team_skills("coding")

        assert "web-research" in research_skills
        assert "code-review" in coding_skills

    def test_list_skills_default_team(self, skills_setup, monkeypatch):
        """Test listing skills for default team (nonexistent)."""
        import agentic_fleet.skills.repository as repo_module

        monkeypatch.setattr(repo_module, "SKILLS_BASE_PATH", skills_setup)

        skills = list_team_skills("nonexistent")
        assert skills == []


class TestLoadSkill:
    """Tests for loading skills."""

    @pytest.fixture
    def skills_setup(self, tmp_path):
        """Set up test skill directory structure."""
        skills_path = tmp_path / "skills"

        # Default team skill
        default_dir = skills_path / "default"
        default_dir.mkdir(parents=True)
        default_skill = default_dir / "general"
        default_skill.mkdir(parents=True)
        (default_skill / "SKILL.md").write_text("""---
skill_id: general
name: General
version: 1.0.0
description: Test
team_id: default
tags: [test]
---
# Purpose
Test

# When to Use
Test

# How to Apply
Test

# Example
Test
""")

        return skills_path

    def test_load_skill_from_team(self, skills_setup, monkeypatch):
        """Test loading skill from specific team."""
        import agentic_fleet.skills.repository as repo_module

        monkeypatch.setattr(repo_module, "SKILLS_BASE_PATH", skills_setup)

        skill = load_skill("general", team_id="default")
        assert skill is not None
        assert skill.metadata.skill_id == "general"

    def test_load_nonexistent_skill(self, skills_setup, monkeypatch):
        """Test loading nonexistent skill returns None."""
        import agentic_fleet.skills.repository as repo_module

        monkeypatch.setattr(repo_module, "SKILLS_BASE_PATH", skills_setup)

        skill = load_skill("nonexistent")
        assert skill is None


class TestSkillExists:
    """Tests for checking skill existence."""

    @pytest.fixture
    def skills_setup(self, tmp_path):
        """Set up test skill directory structure."""
        skills_path = tmp_path / "skills"
        default_dir = skills_path / "default"
        default_dir.mkdir(parents=True)
        general_skill = default_dir / "general"
        general_skill.mkdir(parents=True)
        (general_skill / "SKILL.md").write_text("test")
        return skills_path

    def test_skill_exists(self, skills_setup, monkeypatch):
        """Test checking if skill exists."""
        import agentic_fleet.skills.repository as repo_module

        monkeypatch.setattr(repo_module, "SKILLS_BASE_PATH", skills_setup)

        assert skill_exists("general") is True
        assert skill_exists("nonexistent") is False
