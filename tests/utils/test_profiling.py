"""Tests for performance profiling utilities."""

from __future__ import annotations

import asyncio
import logging
import time

import pytest

from agentic_fleet.utils.profiling import (
    PerformanceTracker,
    get_performance_stats,
    log_performance_summary,
    profile_function,
    reset_performance_stats,
    timed_operation,
    track_operation,
)


def test_timed_operation_fast(caplog):
    """Test timed_operation for fast operations."""
    with caplog.at_level(logging.DEBUG), timed_operation("fast_operation", threshold_ms=100):
        time.sleep(0.01)  # 10ms

    # Should only log debug, not warning
    assert "fast_operation completed in" in caplog.text
    assert "Slow operation" not in caplog.text


def test_timed_operation_slow(caplog):
    """Test timed_operation for slow operations."""
    with caplog.at_level(logging.WARNING), timed_operation("slow_operation", threshold_ms=10):
        time.sleep(0.02)  # 20ms

    # Should log warning for slow operation
    assert "Slow operation" in caplog.text
    assert "slow_operation took" in caplog.text


def test_profile_function_sync():
    """Test profile_function decorator with synchronous function."""

    @profile_function(threshold_ms=100)
    def sample_function(x: int) -> int:
        time.sleep(0.01)
        return x * 2

    result = sample_function(5)
    assert result == 10


@pytest.mark.asyncio
async def test_profile_function_async():
    """Test profile_function decorator with asynchronous function."""

    @profile_function(threshold_ms=100)
    async def async_sample(x: int) -> int:
        await asyncio.sleep(0.01)
        return x * 2

    result = await async_sample(5)
    assert result == 10


def test_performance_tracker_basic():
    """Test basic PerformanceTracker functionality."""
    tracker = PerformanceTracker()

    with tracker.track("operation1"):
        time.sleep(0.01)

    with tracker.track("operation1"):
        time.sleep(0.02)

    stats = tracker.get_stats("operation1")
    assert stats["count"] == 2
    assert stats["avg_ms"] > 0
    assert stats["min_ms"] > 0
    assert stats["max_ms"] > stats["min_ms"]


def test_performance_tracker_multiple_operations():
    """Test tracker with multiple different operations."""
    tracker = PerformanceTracker()

    with tracker.track("op1"):
        time.sleep(0.01)

    with tracker.track("op2"):
        time.sleep(0.02)

    all_stats = tracker.get_all_stats()
    assert "op1" in all_stats
    assert "op2" in all_stats
    assert all_stats["op1"]["count"] == 1
    assert all_stats["op2"]["count"] == 1


def test_performance_tracker_reset():
    """Test resetting tracker statistics."""
    tracker = PerformanceTracker()

    with tracker.track("operation"):
        time.sleep(0.01)

    assert tracker.get_stats("operation")["count"] == 1

    tracker.reset("operation")
    assert tracker.get_stats("operation")["count"] == 0


def test_performance_tracker_reset_all():
    """Test resetting all tracker statistics."""
    tracker = PerformanceTracker()

    with tracker.track("op1"):
        time.sleep(0.01)

    with tracker.track("op2"):
        time.sleep(0.01)

    tracker.reset()
    assert tracker.get_stats("op1")["count"] == 0
    assert tracker.get_stats("op2")["count"] == 0


def test_performance_tracker_log_summary(caplog):
    """Test logging performance summary."""
    tracker = PerformanceTracker()

    with tracker.track("test_op"):
        time.sleep(0.01)

    with caplog.at_level(logging.INFO):
        tracker.log_summary()

    assert "Performance Summary" in caplog.text
    assert "test_op" in caplog.text


def test_performance_tracker_empty_summary(caplog):
    """Test logging summary when no data is tracked."""
    tracker = PerformanceTracker()

    with caplog.at_level(logging.INFO):
        tracker.log_summary()

    assert "No performance data tracked" in caplog.text


def test_global_track_operation():
    """Test global track_operation function."""
    reset_performance_stats()  # Start fresh

    with track_operation("global_op"):
        time.sleep(0.01)

    stats = get_performance_stats("global_op")
    assert stats["count"] == 1
    assert stats["avg_ms"] > 0


def test_global_performance_stats():
    """Test global get_performance_stats function."""
    reset_performance_stats()  # Start fresh

    with track_operation("op1"):
        time.sleep(0.01)

    with track_operation("op2"):
        time.sleep(0.01)

    all_stats = get_performance_stats()
    assert "op1" in all_stats
    assert "op2" in all_stats


def test_global_log_summary(caplog):
    """Test global log_performance_summary function."""
    reset_performance_stats()  # Start fresh

    with track_operation("test_op"):
        time.sleep(0.01)

    with caplog.at_level(logging.INFO):
        log_performance_summary()

    assert "Performance Summary" in caplog.text
    assert "test_op" in caplog.text


def test_global_reset():
    """Test global reset_performance_stats function."""
    reset_performance_stats()  # Start fresh

    with track_operation("op"):
        time.sleep(0.01)

    assert get_performance_stats("op")["count"] == 1

    reset_performance_stats("op")
    assert get_performance_stats("op")["count"] == 0


def test_timed_operation_with_exception():
    """Test that timed_operation still logs when an exception occurs."""

    with pytest.raises(ValueError, match="Test error"), timed_operation("failing_op"):
        raise ValueError("Test error")

    # Should still track timing even on exception


def test_performance_tracker_no_stats():
    """Test getting stats for non-existent operation."""
    tracker = PerformanceTracker()
    stats = tracker.get_stats("nonexistent")

    assert stats["count"] == 0
    assert stats["avg_ms"] == 0
    assert stats["min_ms"] == 0
    assert stats["max_ms"] == 0
