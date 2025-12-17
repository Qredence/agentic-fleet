"""Memory usage helpers.

Uses `psutil` (already a project dependency) to report process RSS in a
platform-consistent way.
"""

from __future__ import annotations

import os

import psutil


def get_process_rss_bytes(pid: int | None = None) -> int:
    """Return resident set size (RSS) in bytes for the given PID (or current process)."""
    process = psutil.Process(pid or os.getpid())
    return int(process.memory_info().rss)


def get_process_rss_mb(pid: int | None = None) -> float:
    """Return resident set size (RSS) in MB for the given PID (or current process)."""
    return get_process_rss_bytes(pid) / (1024 * 1024)
