"""Unit tests for ContextModulator middleware."""

import asyncio

import pytest
import sys
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agentic_fleet.middleware.context import ContextModulator
from agentic_fleet import config


class TestContextModulatorScope:
    """Tests for ContextModulator.scope context manager."""

    @pytest.mark.asyncio
    async def test_scope_activates_team(self, reset_team_registry):
        """Test that scope activates the correct team."""
        async with ContextModulator.scope("research") as ctx:
            assert ctx is not None
            assert ctx["team_id"] == "research"
            assert "browser" in ctx["tools"]

    @pytest.mark.asyncio
    async def test_scope_returns_team_context(self, reset_team_registry):
        """Test that scope returns TeamContext dict."""
        async with ContextModulator.scope("coding") as ctx:
            assert isinstance(ctx, dict)
            assert ctx["team_id"] == "coding"
            assert "repo_read" in ctx["tools"]

    @pytest.mark.asyncio
    async def test_scope_resets_after_exit(self, reset_team_registry):
        """Test that context is reset after exiting scope."""
        # Before scope
        before = ContextModulator.get_current()
        assert before is None

        async with ContextModulator.scope("default"):
            during = ContextModulator.get_current()
            assert during is not None
            assert during["team_id"] == "default"

        # After scope
        after = ContextModulator.get_current()
        assert after is None

    @pytest.mark.asyncio
    async def test_nested_scopes(self, reset_team_registry):
        """Test that nested scopes work correctly."""
        async with ContextModulator.scope("research"):
            outer = ContextModulator.get_current()
            assert outer["team_id"] == "research"

            async with ContextModulator.scope("coding"):
                inner = ContextModulator.get_current()
                assert inner["team_id"] == "coding"

            # After inner scope exits, should be back to outer
            restored = ContextModulator.get_current()
            assert restored["team_id"] == "research"


class TestContextModulatorGetCurrent:
    """Tests for ContextModulator.get_current()."""

    @pytest.mark.asyncio
    async def test_get_current_returns_none_outside_scope(self, reset_team_registry):
        """Test get_current returns None when no scope is active."""
        result = ContextModulator.get_current()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_returns_context_inside_scope(self, reset_team_registry):
        """Test get_current returns context when inside scope."""
        async with ContextModulator.scope("research") as ctx:
            result = ContextModulator.get_current()
            assert result == ctx

    @pytest.mark.asyncio
    async def test_get_current_contains_team_id(self, reset_team_registry):
        """Test get_current returns context with team_id."""
        async with ContextModulator.scope("default") as ctx:
            result = ContextModulator.get_current()
            assert "team_id" in result
            assert result["team_id"] == "default"


class TestContextModulatorDefaultFallback:
    """Tests for default team fallback behavior."""

    @pytest.mark.asyncio
    async def test_unknown_team_falls_back_to_default(self, reset_team_registry):
        """Test that unknown team falls back to default."""
        async with ContextModulator.scope("unknown_team") as ctx:
            assert ctx["team_id"] == "default"

    @pytest.mark.asyncio
    async def test_unknown_team_gets_default_tools(self, reset_team_registry):
        """Test that unknown team gets default tools."""
        async with ContextModulator.scope("nonexistent") as ctx:
            assert ctx["tools"] == config.TEAM_REGISTRY["default"]["tools"]


class TestContextModulatorTeamRegistry:
    """Tests for team registry integration."""

    @pytest.mark.asyncio
    async def test_research_team_has_correct_tools(self, reset_team_registry):
        """Test research team has browser/search tools."""
        async with ContextModulator.scope("research") as ctx:
            assert "browser" in ctx["tools"]
            assert "search" in ctx["tools"]

    @pytest.mark.asyncio
    async def test_coding_team_has_correct_tools(self, reset_team_registry):
        """Test coding team has repo tools."""
        async with ContextModulator.scope("coding") as ctx:
            assert "repo_read" in ctx["tools"]
            assert "repo_write" in ctx["tools"]

    @pytest.mark.asyncio
    async def test_default_team_has_general_tools(self, reset_team_registry):
        """Test default team has general tools."""
        async with ContextModulator.scope("default") as ctx:
            assert "general" in ctx["tools"]


class TestContextModulatorAsyncSafety:
    """Tests for async context safety."""

    @pytest.mark.asyncio
    async def test_context_isolation_between_tasks(self, reset_team_registry):
        """Test that contexts are isolated between concurrent tasks."""
        import asyncio

        async def task(team_id):
            async with ContextModulator.scope(team_id):
                await asyncio.sleep(0.01)  # Small delay
                return ContextModulator.get_current()["team_id"]

        # Run two tasks concurrently
        results = await asyncio.gather(
            task("research"),
            task("coding"),
        )

        # Each task should see its own team
        assert results[0] == "research"
        assert results[1] == "coding"

    @pytest.mark.asyncio
    async def test_context_persists_across_awaits(self, reset_team_registry):
        """Test that context persists across await points."""
        async with ContextModulator.scope("research") as ctx:
            # Context before await
            before = ContextModulator.get_current()
            assert before["team_id"] == "research"

            # Simulate await
            await asyncio.sleep(0.001)

            # Context after await
            after = ContextModulator.get_current()
            assert after["team_id"] == "research"
