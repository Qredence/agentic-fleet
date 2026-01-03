"""Skill file I/O and SKILL.md parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from agentic_fleet.skills.models import Skill, SkillContext


# Base path for skill storage (relative to this file)
SKILLS_BASE_PATH = Path(__file__).parent.parent / "skills"


class SkillMount:
    """Manages skill mounting in the current execution context."""

    def __init__(self, context: SkillContext):
        self._context = context

    def mount(self, skill_id: str) -> bool:
        """Mount a skill for the current execution context.

        Args:
            skill_id: The skill identifier to mount

        Returns:
            True if skill was successfully mounted, False if not available
        """
        if self._context.is_available(skill_id):
            self._context.add_skill(skill_id)
            return True
        return False

    def unmount(self, skill_id: str) -> bool:
        """Unmount a skill from the current execution context.

        Args:
            skill_id: The skill identifier to unmount

        Returns:
            True if skill was unmounted, False if not mounted
        """
        if self._context.has_skill(skill_id):
            self._context.remove_skill(skill_id)
            return True
        return False

    def mount_multiple(self, skill_ids: list[str]) -> list[str]:
        """Mount multiple skills.

        Args:
            skill_ids: List of skill identifiers to mount

        Returns:
            List of successfully mounted skill IDs
        """
        mounted = []
        for skill_id in skill_ids:
            if self.mount(skill_id):
                mounted.append(skill_id)
        return mounted

    def unmount_all(self) -> None:
        """Unmount all mounted skills."""
        self._context.mounted_skills.clear()

    def get_mounted(self) -> list[str]:
        """Get list of currently mounted skill IDs."""
        return list(self._context.mounted_skills)

    def get_available(self) -> list[str]:
        """Get list of available skill IDs for current team."""
        return list(self._context.available_skill_ids)


def load_skill(skill_id: str, team_id: str | None = None) -> Optional[Skill]:
    """Load a skill from file system.

    Args:
        skill_id: The skill identifier
        team_id: Optional team ID (uses "default" if not provided)

    Returns:
        Skill object if found, None otherwise
    """
    team = team_id or "default"

    # Search in team-specific directory first, then default
    for search_team in [team, "default"]:
        skill_path = SKILLS_BASE_PATH / search_team / skill_id / "SKILL.md"
        if skill_path.exists():
            return _parse_skill_file(skill_path)

    return None


def _parse_skill_file(path: Path) -> Optional[Skill]:
    """Parse a SKILL.md file into a Skill object.

    Args:
        path: Path to the SKILL.md file

    Returns:
        Skill object if parsing succeeds, None otherwise
    """
    content = path.read_text()

    # Split frontmatter and body
    parts = content.split("---")
    if len(parts) < 3:
        return None

    try:
        frontmatter = yaml.safe_load(parts[1])
        body_content = parts[2].strip()

        # Parse body into sections
        sections = {}
        current_section = ""
        current_lines = []

        for line in body_content.split("\n"):
            if line.startswith("# "):
                if current_section:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = line[2:].strip().lower().replace(" ", "_")
                current_lines = []
            else:
                current_lines.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_lines).strip()

        return Skill.from_dict({
            "metadata": frontmatter,
            "content": {
                "purpose": sections.get("purpose", ""),
                "when_to_use": sections.get("when_to_use", ""),
                "how_to_apply": sections.get("how_to_apply", ""),
                "example": sections.get("example", ""),
                "constraints": _parse_list_field(sections.get("constraints", "")),
                "prerequisites": _parse_list_field(sections.get("prerequisites", "")),
            },
        })
    except (yaml.YAMLError, KeyError, TypeError) as e:
        print(f"Error parsing skill file {path}: {e}")
        return None


def _parse_list_field(value: str) -> list[str]:
    """Parse a list field from markdown (comma or newline separated)."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    if "," in value:
        return [v.strip() for v in value.split(",") if v.strip()]
    return [v.strip() for v in value.split("\n") if v.strip()]


def list_team_skills(team_id: str) -> list[str]:
    """List all available skill IDs for a team.

    Args:
        team_id: The team identifier

    Returns:
        List of skill IDs available for the team
    """
    skills_path = SKILLS_BASE_PATH / team_id
    if not skills_path.exists():
        # Check default team skills
        skills_path = SKILLS_BASE_PATH / "default"
    if not skills_path.exists():
        return []

    skills: list[str] = []
    for item in skills_path.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            skills.append(item.name)
    return sorted(skills)


def load_team_skills(team_id: str) -> list[Skill]:
    """Load all available skills for a team as Skill objects.

    Args:
        team_id: The team identifier

    Returns:
        List of Skill objects for the team
    """
    skills: list[Skill] = []
    for skill_id in list_team_skills(team_id):
        skill = load_skill(skill_id, team_id)
        if skill is not None:
            skills.append(skill)
    return skills


def list_all_skills() -> dict[str, list[str]]:
    """List all skills across all teams.

    Returns:
        Dictionary mapping team_id to list of skill IDs
    """
    result: dict[str, list[str]] = {}

    if not SKILLS_BASE_PATH.exists():
        return result

    for team_dir in SKILLS_BASE_PATH.iterdir():
        if team_dir.is_dir():
            skills = list_team_skills(team_dir.name)
            if skills:
                result[team_dir.name] = skills

    return result


def skill_exists(skill_id: str, team_id: str | None = None) -> bool:
    """Check if a skill exists.

    Args:
        skill_id: The skill identifier
        team_id: Optional team ID to search in

    Returns:
        True if skill exists, False otherwise
    """
    team = team_id or "default"
    skill_path = SKILLS_BASE_PATH / team / skill_id / "SKILL.md"
    return skill_path.exists()
