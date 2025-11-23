"""Task utility functions."""

import re


def is_simple_task(task: str) -> bool:
    """Identify trivial heartbeat/greeting tasks that don't need routing."""
    task_lower = task.strip().lower()

    # Keywords that imply real-time or specific entity knowledge
    complex_keywords = [
        "news",
        "latest",
        "current",
        "election",
        "price",
        "stock",
        "weather",
        "who is",
        "who won",
        "who are",
        "mayor",
        "governor",
        "president",
    ]

    # Heartbeat / greeting style tasks that should be answered directly
    trivial_keywords = [
        "ping",
        "hello",
        "hi",
        "hey",
        "test",
        "are you there",
        "you there",
        "you awake",
    ]

    # Keywords that imply a simple deterministic response
    simple_keywords = ["define", "calculate", "solve", "2+", "meaning of"]

    is_time_sensitive = bool(re.search(r"20[2-9][0-9]", task))
    has_complex_keyword = any(
        re.search(r"\b" + re.escape(k) + r"\b", task_lower) for k in complex_keywords
    )
    has_trivial_keyword = any(
        re.search(r"\b" + re.escape(k) + r"\b", task_lower) for k in trivial_keywords
    )
    has_simple_keyword = any(
        re.search(r"\b" + re.escape(k) + r"\b", task_lower) for k in simple_keywords
    )

    # Consider very short, punctuation-free tasks as simple if not time-sensitive
    if is_time_sensitive or has_complex_keyword:
        return False

    return has_trivial_keyword or has_simple_keyword
