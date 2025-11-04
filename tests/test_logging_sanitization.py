"""Tests for logging sanitization helper."""

from __future__ import annotations

import random
from typing import Any

import pytest

from agentic_fleet.utils.logging_sanitize import REMOVED_LOG_CHARS, sanitize_log_value


def test_basic_string_unchanged() -> None:
    original = "workflow-123"
    assert sanitize_log_value(original) == original


def test_non_string_input() -> None:
    assert sanitize_log_value(12345) == "12345"


def test_removal_of_all_control_chars() -> None:
    # Construct a value containing each removed character at least once
    value = "A" + "".join(ch for ch in REMOVED_LOG_CHARS) + "Z"
    sanitized = sanitize_log_value(value)
    for ch in REMOVED_LOG_CHARS:
        assert ch not in sanitized
    # Ensure boundary characters remain
    assert sanitized.startswith("A") and sanitized.endswith("Z")


def test_escape_sequence_removed() -> None:
    colored = "\x1b[31mERROR:\x1b[0m Something happened"
    sanitized = sanitize_log_value(colored)
    assert "\x1b" not in sanitized
    # Bracket payload survives, which is acceptable
    assert "[31mERROR:" in sanitized


def test_random_mixture_property() -> None:
    random.seed(12345)
    population: list[str] = [
        *list("abcdefghijklmnopqrstuvwxyz0123456789-_"),
        *REMOVED_LOG_CHARS,
    ]
    value = "".join(random.choice(population) for _ in range(500))
    sanitized = sanitize_log_value(value)
    for ch in REMOVED_LOG_CHARS:
        assert ch not in sanitized
    # Non-removed characters should remain (sample check)
    for ch in "abc123-_":
        assert ch in sanitized


@pytest.mark.parametrize("value", [None, object()])
def test_resilience_on_unusual_values(value: Any) -> None:
    # Should never raise; result should be a string
    result = sanitize_log_value(value)
    assert isinstance(result, str)
