"""Message classification utilities for fast-path routing.

This module provides utilities to classify incoming messages and determine
whether they should be routed through the fast-path (direct LLM response)
or the full multi-agent orchestration workflow.
"""

import os
import re
from typing import ClassVar

__all__ = ["MessageClassifier", "should_use_fast_path"]


class MessageClassifier:
    """Classifies messages for routing decisions."""

    # Patterns that indicate complex requests requiring full orchestration
    COMPLEXITY_PATTERNS: ClassVar[list[str]] = [
        r"\bcode\b",
        r"\bimplement\b",
        r"\bcreate\b",
        r"\banalyze\b",
        r"\bcompare\b",
        r"\bbuild\b",
        r"\bwrite\b",
        r"\bgenerate\b",
        r"\brefactor\b",
        r"\boptimize\b",
        r"\bdebug\b",
        r"\bfix\b",
        r"\btest\b",
        r"\bdeploy\b",
        r"\breview\b",
        r"\bexplain\b.*\bcode\b",
        r"\bmultiple\b.*\b(steps|tasks|items)\b",
        r"\bstep\s+by\s+step\b",
    ]

    # Simple acknowledgments that definitely use fast-path
    SIMPLE_ACKNOWLEDGMENTS: ClassVar[set[str]] = {
        "ok",
        "okay",
        "yes",
        "no",
        "thanks",
        "thank you",
        "got it",
        "understood",
        "sure",
        "alright",
        "fine",
        "continue",
        "proceed",
        "go ahead",
    }

    def __init__(
        self,
        max_length: int = 100,
        enabled: bool = True,
        custom_patterns: list[str] | None = None,
    ):
        """Initialize the classifier.

        Args:
            max_length: Maximum message length for fast-path eligibility
            enabled: Whether fast-path classification is enabled
            custom_patterns: Additional complexity patterns to check
        """
        self.max_length = max_length
        self.enabled = enabled

        # Compile patterns for efficiency
        patterns = self.COMPLEXITY_PATTERNS.copy()
        if custom_patterns:
            patterns.extend(custom_patterns)
        self.complexity_patterns: list[re.Pattern[str]] = [
            re.compile(pattern, re.IGNORECASE) for pattern in patterns
        ]

    def is_simple_acknowledgment(self, message: str) -> bool:
        """Check if message is a simple acknowledgment.

        Args:
            message: The message to classify

        Returns:
            True if the message is a simple acknowledgment
        """
        normalized = message.lower().strip().rstrip(".!?")
        return normalized in self.SIMPLE_ACKNOWLEDGMENTS

    def has_complexity_indicators(self, message: str) -> bool:
        """Check if message contains complexity indicators.

        Args:
            message: The message to classify

        Returns:
            True if complexity indicators are found
        """
        return any(pattern.search(message) for pattern in self.complexity_patterns)

    def classify(self, message: str) -> bool:
        """Classify whether a message should use fast-path.

        Args:
            message: The message to classify

        Returns:
            True if fast-path should be used, False otherwise
        """
        if not self.enabled:
            return False

        # Always use fast-path for simple acknowledgments
        if self.is_simple_acknowledgment(message):
            return True

        # Reject if too long
        if len(message) > self.max_length:
            return False

        # Reject if complexity indicators present
        if self.has_complexity_indicators(message):
            return False

        # Check for multiple sentences (complexity indicator)
        sentence_endings = message.count(".") + message.count("?") + message.count("!")

        # Simple, short messages without complexity indicators use fast-path
        return sentence_endings <= 1


# Global classifier instance
_classifier: MessageClassifier | None = None


def _get_classifier() -> MessageClassifier:
    """Get or create the global classifier instance.

    Returns:
        The global MessageClassifier instance
    """
    global _classifier
    if _classifier is None:
        # Parse boolean: accept "1"/"0" or "true"/"false" (case-insensitive)
        enabled_str = os.getenv("ENABLE_FAST_PATH", "1").lower()
        enabled = enabled_str in {"1", "true"}
        max_length = int(os.getenv("FAST_PATH_MAX_LENGTH", "100"))
        _classifier = MessageClassifier(max_length=max_length, enabled=enabled)
    return _classifier


def should_use_fast_path(message: str) -> bool:
    """Determine if a message should use the fast-path workflow.

    This is the main entry point for fast-path classification.
    It uses environment variables for configuration:
    - ENABLE_FAST_PATH: Enable/disable fast-path (default: true)
      Accepted values: "1", "true", "yes" (case-insensitive) for enabled
    - FAST_PATH_MAX_LENGTH: Maximum message length (default: 100)

    Args:
        message: The user message to classify

    Returns:
        True if the message should use fast-path, False otherwise

    Examples:
        >>> should_use_fast_path("ok")
        True
        >>> should_use_fast_path("implement a new feature")
        False
    """
    classifier = _get_classifier()
    return classifier.classify(message)
