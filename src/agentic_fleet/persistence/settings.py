"""Settings for persistence layer."""

from __future__ import annotations

import os
from pathlib import Path


class PersistenceSettings:
    """Configuration settings for conversation persistence."""

    def __init__(self) -> None:
        """Initialize persistence settings from environment."""
        # Enable/disable persistence
        self.enabled = os.getenv("ENABLE_PERSISTENCE", "true").lower() == "true"

        # Database path
        default_db_path = Path("var/agenticfleet/conversations.db")
        self.db_path = Path(os.getenv("DB_PATH", str(default_db_path)))

        # Summarization settings
        self.summary_threshold = int(os.getenv("CONVERSATION_SUMMARY_THRESHOLD", "20"))
        self.summary_keep_recent = int(os.getenv("CONVERSATION_SUMMARY_KEEP_RECENT", "6"))

        # Event sequencing
        self.enable_sequencing = os.getenv("ENABLE_EVENT_SEQUENCING", "true").lower() == "true"

        # Ledger tracking
        self.enable_ledger = os.getenv("ENABLE_LEDGER_TRACKING", "true").lower() == "true"

        # Reasoning trace storage
        self.enable_reasoning_traces = (
            os.getenv("ENABLE_REASONING_TRACES", "true").lower() == "true"
        )


def get_persistence_settings() -> PersistenceSettings:
    """Get persistence settings instance.

    Returns:
        Persistence settings
    """
    return PersistenceSettings()
