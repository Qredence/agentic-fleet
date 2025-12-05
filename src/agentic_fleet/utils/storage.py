"""
Consolidated storage utilities surface.

This module provides a single import location for storage-related helpers such as
Cosmos helpers, history management, persistence, and job stores. Existing modules
remain unchanged; this file simply re-exports them for convenience.
"""

from __future__ import annotations

from . import cosmos as cosmos_storage
from .cosmos import (
    get_default_user_id,
    is_cosmos_enabled,
    mirror_cache_entry,
    mirror_execution_history,
    record_dspy_optimization_run,
)
from .history_manager import HistoryManager
from .job_store import InMemoryJobStore, JobStore
from .persistence import ConversationPersistenceService, DatabaseManager, PersistenceSettings

__all__ = [
    "ConversationPersistenceService",
    "DatabaseManager",
    "HistoryManager",
    "InMemoryJobStore",
    "JobStore",
    "PersistenceSettings",
    "cosmos_storage",
    "get_default_user_id",
    "is_cosmos_enabled",
    "mirror_cache_entry",
    "mirror_execution_history",
    "record_dspy_optimization_run",
]
