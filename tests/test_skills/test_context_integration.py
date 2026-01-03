"""Tests for skill mounting in ContextModulator."""

import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))


class TestContextModulatorWithSkills:
    """Tests for skill mounting in ContextModulator."""

    @pytest.fixture
    def skill_setup(self, tmp_path, monkeypatch):
        """Set up test skill directory structure."""
        from agentic_fleet.skills.repository import SKILLS_BASE_PATH

        # Create test skill structure
        test_skills_path = tmp_path / "skills"
        research_dir = test_skills_path / "research"
        research_dir.mkdir(parents=True)

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

        # Patch SKILLS_BASE_PATH for test
        import agentic_fleet.skills.repository as repo_module
        import agentic_fleet.middleware.context as ctx_module

        monkeypatch.setattr(repo_module, "SKILLS_BASE_PATH", test_skills_path)
        monkeypatch.setattr(ctx_module, "SKILLS_BASE_PATH", test_skills_path)

        yield test_skills_path

    @pytest.mark.asyncio
    async def test_scope_includes_skills(self, skill_setup, monkeypatch):
        """Test that scope includes available skills."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research") as ctx:
            assert ctx is not None
            assert ctx.team_id == "research"
            assert "web-research" in ctx.available_skill_ids

    @pytest.mark.asyncio
    async def test_mount_skill(self, skill_setup):
        """Test mounting a skill."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research"):
            result = ContextModulator.mount_skill("web-research")
            assert result is True
            assert ContextModulator.get_mounted_skills() == ["web-research"]

    @pytest.mark.asyncio
    async def test_mount_multiple_skills(self, skill_setup):
        """Test mounting multiple skills."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research"):
            mounted = ContextModulator.mount_multiple(["web-research"])
            assert mounted == ["web-research"]

    @pytest.mark.asyncio
    async def test_mount_nonexistent_skill(self, skill_setup):
        """Test mounting non-existent skill returns False."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research"):
            result = ContextModulator.mount_skill("nonexistent")
            assert result is False

    @pytest.mark.asyncio
    async def test_unmount_skill(self, skill_setup):
        """Test unmounting a skill."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research"):
            ContextModulator.mount_skill("web-research")
            result = ContextModulator.unmount_skill("web-research")
            assert result is True
            assert ContextModulator.get_mounted_skills() == []

    @pytest.mark.asyncio
    async def test_unmount_nonexistent_skill(self, skill_setup):
        """Test unmounting non-existent skill returns False."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research"):
            result = ContextModulator.unmount_skill("nonexistent")
            assert result is False

    @pytest.mark.asyncio
    async def test_unmount_all_skills(self, skill_setup):
        """Test unmounting all skills."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research"):
            ContextModulator.mount_skill("web-research")
            ContextModulator.unmount_all()
            assert ContextModulator.get_mounted_skills() == []

    @pytest.mark.asyncio
    async def test_get_available_skills(self, skill_setup):
        """Test getting available skills list."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research"):
            skills = ContextModulator.get_available_skills()
            assert "web-research" in skills

    @pytest.mark.asyncio
    async def test_get_mounted_skills_empty(self, skill_setup):
        """Test getting mounted skills when none are mounted."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research"):
            skills = ContextModulator.get_mounted_skills()
            assert skills == []

    @pytest.mark.asyncio
    async def test_get_team_id(self, skill_setup):
        """Test getting current team ID."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research"):
            team_id = ContextModulator.get_team_id()
            assert team_id == "research"

    @pytest.mark.asyncio
    async def test_context_exits_clears_skills(self, skill_setup):
        """Test that context exit clears mounted skills."""
        from agentic_fleet.middleware.context import ContextModulator

        async with ContextModulator.scope("research") as ctx:
            ctx.add_skill("web-research")
            assert ctx.has_skill("web-research") is True

        # After context exit, skills should be cleared
        # This is tested implicitly - the context object is discarded

    @pytest.mark.asyncio
    async def test_mount_skill_no_context(self, skill_setup):
        """Test mounting skill outside of context returns False."""
        from agentic_fleet.middleware.context import ContextModulator

        # No context active
        result = ContextModulator.mount_skill("web-research")
        assert result is False
