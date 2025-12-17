"""Utility functions for DSPyReasoner.

This module contains helper functions extracted from reasoner.py to reduce
its size and improve maintainability.
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import dspy

from ..utils.cfg import load_config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class FastPathDetector:
    """Robust detection for tasks that can bypass the full agent orchestration."""

    def __init__(self, max_words: int = 60) -> None:
        self.max_words = max_words

        # 1. Complex Intent Patterns (Immediate Disqualification)
        # These imply a need for planning, multi-step reasoning, or deep research.
        self.complex_patterns = [
            r"\b(create|plan|design|build|architect)\b.*?\b(detailed|comprehensive|full)\b",
            r"\b(write|draft)\b.*?\b(report|article|paper|essay)\b",
            r"\b(develop|implement|code)\b.*?\b(program|software|application|system)\b",
            r"\b(analyze|evaluate)\b.*?\b(report|data|results)\b",
            r"\b(summarize)\b.*?\b(detailed|comprehensive)\b",
            r"\b(compare|contrast)\b.*?\b(multiple|different)\b",
        ]

        # 2. Length-based disqualification (override keyword matching)
        # Very long queries are more likely to be complex.
        self.max_length_words = max_words  # Default 60 words

        # 3. Simple Intent Patterns (Qualification)
        # These are greetings, simple questions, or factual lookups.
        self.simple_intents = [
            r"^hi\b",
            r"^hello\b",
            r"^hey\b",
            r"^how are you",
            r"^what('?s| is) your name",
            r"^who are you",
            r"^thank you",
            r"^thanks",
            r"^bye\b",
            r"^goodbye",
            r"^see you",
            r"^what time is it",
            r"^what('?s| is) the time",
            r"^what('?s| is) today'?s date",
            r"^what date is it",
            r"\b(hello|hi|hey|greetings)\b.*\?$",  # Greeting questions
            r"^\d+\s*[\+\-\*\/]\s*\d+",  # Simple arithmetic: "2 + 2"
            r"^calculate\s+\d+",  # "calculate 42"
            r"^what is \d+",  # "what is 42"
            r"^\d+$",  # Just a number
        ]

    def classify(self, task: str) -> bool:
        """Classify a task as simple enough for fast-path handling.

        Args:
            task: The user's task description

        Returns:
            True if task is simple, False otherwise
        """
        task_lower = task.strip().lower()

        # 1. Check Length (override)
        word_count = len(task_lower.split())
        if word_count > self.max_length_words:
            return False

        # 2. Check Complex Patterns (immediate disqualification)
        for pattern in self.complex_patterns:
            if re.search(pattern, task_lower):
                return False

        # 3. Check Qualifiers (Simple Intents)
        for pattern in self.simple_intents:
            if re.search(pattern, task_lower):
                return True

        # 4. Fallback: If very short and not complex, assume simple (chatty)
        return word_count < 5


def is_simple_task(task: str, max_words: int | None = None) -> bool:
    """Wrapper for FastPathDetector classification."""
    detector = FastPathDetector(max_words=max_words if max_words is not None else 60)
    return detector.classify(task)


def is_time_sensitive_task(task: str) -> bool:
    """Heuristic detection for queries that require fresh, web-sourced data."""
    task_lower = task.lower()
    freshness_keywords = [
        "today",
        "now",
        "current",
        "latest",
        "recent",
        "breaking",
        "this week",
        "this month",
    ]

    if any(keyword in task_lower for keyword in freshness_keywords):
        return True

    # Detect explicit four-digit years 2023+ (signals recency)
    match = re.search(r"\b(20[2-9][0-9])\b", task)
    if match:
        year = int(match.group(1))
        if year >= 2023:
            return True

    return False


def _search_bases() -> list[Path]:
    """Search for valid base directories to resolve compiled reasoner path."""
    resolved = Path(__file__).resolve()
    parents = resolved.parents
    repo_root = parents[3] if len(parents) > 3 else parents[-1]
    package_root = parents[1] if len(parents) > 1 else parents[-1]
    module_dir = resolved.parent
    return [repo_root, package_root, module_dir, Path.cwd()]


@lru_cache(maxsize=1)
def _resolve_compiled_reasoner_path() -> Path:
    """Resolve the path to compiled DSPy reasoner artifact."""
    config: dict[str, Any] = {}
    try:
        config = load_config(validate=False)
    except Exception as exc:  # pragma: no cover - best-effort fallback
        logger.debug("Failed to load workflow config for compiled reasoner path: %s", exc)

    dspy_config = config.get("dspy", {})
    relative_path = Path(
        dspy_config.get("compiled_reasoner_path", ".var/cache/dspy/compiled_reasoner.json")
    ).expanduser()
    if relative_path.is_absolute():
        return relative_path

    bases = _search_bases()
    for base in bases:
        candidate = (base / relative_path).resolve()
        if candidate.exists():
            return candidate

    return (bases[0] / relative_path).resolve()


def get_configured_compiled_reasoner_path() -> Path:
    """Return the configured path to the compiled DSPy reasoner artifact."""
    return _resolve_compiled_reasoner_path()


def _load_compiled_module(compiled_path: Path) -> dspy.Module | None:
    """Attempt to load optimized prompt weights from disk."""
    if compiled_path.exists():
        try:
            logger.info(f"Loading compiled reasoner from {compiled_path}")
            from .reasoner import DSPyReasoner

            reasoner = DSPyReasoner()
            reasoner.load(str(compiled_path))
            logger.debug("Successfully loaded compiled DSPy prompts.")
            return reasoner
        except Exception as e:
            logger.warning(f"Failed to load compiled reasoner: {e}")
            return None
    else:
        logger.debug(
            "No compiled reasoner found at %s. Using default zero-shot prompts.",
            compiled_path,
        )
        return None


def _generate_cache_key(task: str, team_key: str = "") -> str:
    """Generate cache key from task and team description.

    Args:
        task: Task string
        team_key: Optional team description string

    Returns:
        MD5 hash as cache key
    """
    content = f"{task}:{team_key}" if team_key else task
    # MD5 used for cache key generation, not security
    return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()


def _should_cache_routing(
    enable_routing_cache: bool,
    _cache_ttl_seconds: int,
    task_complexity: str = "medium",
) -> bool:
    """Determine if routing should be cached based on complexity and settings."""
    if not enable_routing_cache:
        return False

    # Don't cache highly complex tasks - they're more likely to be unique
    return task_complexity != "high"


def _validate_prediction_fields(prediction: Any, required_fields: list[str]) -> bool:
    """Validate that prediction has all required fields."""
    for field in required_fields:
        if not hasattr(prediction, field):
            logger.warning(f"Prediction missing required field: {field}")
            return False
    return True


def _format_team_description(agents: dict[str, Any]) -> str:
    """Format agent team description for routing prompts."""
    if not agents:
        return "No agents available"

    descriptions = []
    for name, agent in agents.items():
        desc = f"**{name}**: "
        if hasattr(agent, "description") and agent.description:
            desc += agent.description
        elif hasattr(agent, "instructions") and agent.instructions:
            desc += agent.instructions[:100] + "..."
        else:
            desc += "General-purpose agent"
        descriptions.append(desc)

    return "\n".join(descriptions)


# Module-level cache for DSPy module instances (stateless, can be shared)
_MODULE_CACHE: dict[str, dspy.Module] = {}


def get_cached_module(key: str, factory_function, *args, **kwargs) -> dspy.Module:
    """Get or create a cached DSPy module."""
    if key not in _MODULE_CACHE:
        _MODULE_CACHE[key] = factory_function(*args, **kwargs)
    return _MODULE_CACHE[key]


def get_reasoner_source_hash() -> str:
    """Return a stable hash of the DSPy reasoner source files.

    Used to invalidate compiled DSPy artifacts when the underlying reasoner
    or signature code changes.
    """
    module_dir = Path(__file__).resolve().parent
    files = [
        module_dir / "reasoner.py",
        module_dir / "reasoner_utils.py",
        module_dir / "reasoner_cache.py",
        module_dir / "reasoner_modules.py",
        module_dir / "reasoner_predictions.py",
        module_dir / "signatures.py",
        module_dir / "typed_models.py",
        module_dir / "assertions.py",
        module_dir / "nlu.py",
        module_dir / "nlu_signatures.py",
        module_dir / "handoff_signatures.py",
        module_dir / "answer_quality.py",
    ]

    digest = hashlib.sha256()
    for path in files:
        try:
            digest.update(path.read_bytes())
        except OSError:
            # Missing files shouldn't crash runtime; treat as empty contribution.
            continue

    return digest.hexdigest()[:16]
