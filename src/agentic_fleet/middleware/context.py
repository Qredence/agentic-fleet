"""Context modulator for team-specific runtime configuration with skill mounting."""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Optional

from agentic_fleet.config import TEAM_REGISTRY
from agentic_fleet.skills.models import SkillContext
from agentic_fleet.skills.repository import load_team_skills


_active_context: ContextVar[SkillContext | None] = ContextVar("fleet_context", default=None)
SKILLS_BASE_PATH = Path(__file__).parent.parent / "skills"


class ContextModulator:
    """Middleware that swaps the active environment based on the team with skill support."""

    @staticmethod
    @asynccontextmanager
    async def scope(team_id: str):
        """Temporarily activate the team context for this async scope.

        Args:
            team_id: The team identifier to scope to
        """
        resolved_team = team_id if team_id in TEAM_REGISTRY else "default"
        base_context = TEAM_REGISTRY.get(resolved_team, TEAM_REGISTRY["default"])

        # Get available skills for team
        available_skills = load_team_skills(resolved_team)

        context_data = SkillContext(
            team_id=resolved_team,
            tools=list(base_context.get("tools", [])),
            constraints=[],
            mounted_skills=[],
            available_skills=available_skills,
        )

        token = _active_context.set(context_data)
        try:
            yield context_data
        finally:
            _active_context.reset(token)

    @staticmethod
    def get_current() -> Optional[SkillContext]:
        """Return the currently active team context, if any."""
        return _active_context.get()

    @staticmethod
    def mount_skill(skill_id: str) -> bool:
        """Mount a skill for the current execution context.

        Args:
            skill_id: The skill identifier to mount

        Returns:
            True if skill was successfully mounted, False if not available
        """
        ctx = _active_context.get()
        if ctx is None:
            return False

        if ctx.is_available(skill_id):
            ctx.add_skill(skill_id)
            return True
        return False

    @staticmethod
    def unmount_skill(skill_id: str) -> bool:
        """Unmount a skill from the current execution context.

        Args:
            skill_id: The skill identifier to unmount

        Returns:
            True if skill was unmounted, False if not mounted
        """
        ctx = _active_context.get()
        if ctx is None:
            return False

        if ctx.has_skill(skill_id):
            ctx.remove_skill(skill_id)
            return True
        return False

    @staticmethod
    def mount_multiple(skill_ids: list[str]) -> list[str]:
        """Mount multiple skills.

        Args:
            skill_ids: List of skill identifiers to mount

        Returns:
            List of successfully mounted skill IDs
        """
        mounted = []
        for skill_id in skill_ids:
            if ContextModulator.mount_skill(skill_id):
                mounted.append(skill_id)
        return mounted

    @staticmethod
    def unmount_all() -> None:
        """Unmount all mounted skills."""
        ctx = _active_context.get()
        if ctx is not None:
            ctx.mounted_skills.clear()

    @staticmethod
    def get_mounted_skills() -> list[str]:
        """Get list of currently mounted skills.

        Returns:
            List of mounted skill IDs
        """
        ctx = _active_context.get()
        return list(ctx.mounted_skills) if ctx else []

    @staticmethod
    def get_available_skills() -> list[str]:
        """Get list of available skills for current team.

        Returns:
            List of available skill IDs
        """
        ctx = _active_context.get()
        return list(ctx.available_skill_ids) if ctx else []

    @staticmethod
    def get_team_id() -> str | None:
        """Get the current team ID.

        Returns:
            Current team ID or None if no context
        """
        ctx = _active_context.get()
        return ctx.team_id if ctx else None
