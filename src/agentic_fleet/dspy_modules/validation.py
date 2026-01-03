"""Reusable Pydantic validation helpers for DSPy models."""

from __future__ import annotations

from typing import Iterable

from agentic_fleet.config import TeamRegistry

VALID_ROUTING_PATTERNS = {
    "direct",
    "simple",
    "complex",
    "direct_answer",
    "simple_tool",
    "complex_council",
}


def validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must be non-empty.")
    return cleaned


def validate_string_list(values: list[str], field_name: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list of strings.")
    cleaned: list[str] = []
    for item in values:
        cleaned.append(validate_non_empty_str(item, f"{field_name}[]"))
    return cleaned


def validate_team_name(value: str) -> str:
    value = validate_non_empty_str(value, "team_id")
    if value not in TeamRegistry:
        known = ", ".join(sorted(TeamRegistry.keys()))
        raise ValueError(f"Unknown team_id '{value}'. Known teams: {known}.")
    return value


def validate_routing_pattern(value: str) -> str:
    value = validate_non_empty_str(value, "pattern")
    if value not in VALID_ROUTING_PATTERNS:
        known = ", ".join(sorted(VALID_ROUTING_PATTERNS))
        raise ValueError(f"Unknown routing pattern '{value}'. Known patterns: {known}.")
    return value


def validate_optional_str_list(values: list[str] | None, field_name: str) -> list[str]:
    if values is None:
        return []
    return validate_string_list(values, field_name)
