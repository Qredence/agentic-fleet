"""Team registry and shared configuration."""

from __future__ import annotations

from typing import Any, TypedDict


class TeamConfig(TypedDict):
    """Configuration for a team environment."""

    tools: list[str]
    credentials: dict[str, Any]
    description: str


class TeamContext(TeamConfig):
    """Runtime context includes the resolved team identifier."""

    team_id: str


TEAM_REGISTRY: dict[str, TeamConfig] = {
    "research": {
        "tools": ["browser", "search"],
        "credentials": {},
        "description": "Web research and synthesis.",
    },
    "coding": {
        "tools": ["repo_read", "repo_write", "tests"],
        "credentials": {},
        "description": "Code changes and validation.",
    },
    "default": {
        "tools": [],
        "credentials": {},
        "description": "Fallback generalist team.",
    },
}

# Backwards-compatible alias for earlier Phase 1 usage.
TeamRegistry = TEAM_REGISTRY


def list_teams() -> set[str]:
    """Return the set of known team identifiers."""
    return set(TEAM_REGISTRY.keys())
