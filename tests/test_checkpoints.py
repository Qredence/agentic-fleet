import pytest

from agenticfleet.core.checkpoints import _parse_timestamp


def test_parse_timestamp_with_valid_iso_string() -> None:
    assert isinstance(_parse_timestamp("2023-10-27T10:00:00Z"), float)


def test_parse_timestamp_with_valid_float() -> None:
    assert isinstance(_parse_timestamp(1635331200.0), float)


def test_parse_timestamp_with_invalid_string() -> None:
    with pytest.raises(ValueError):
        _parse_timestamp("invalid-timestamp")


def test_parse_timestamp_with_none() -> None:
    """None timestamps return -inf for sorting to the end."""
    assert _parse_timestamp(None) == float("-inf")
