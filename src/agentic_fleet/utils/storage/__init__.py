"""Storage submodule: Cosmos DB, persistence, history, and job stores.

This submodule provides an organized interface to storage-related
utilities. All exports are backward-compatible with direct imports from
utils.cosmos, utils.persistence, utils.history_manager, and utils.job_store.

Usage:
    from agentic_fleet.utils.storage import HistoryManager, is_cosmos_enabled
    # or
    from agentic_fleet.utils.cosmos import is_cosmos_enabled  # still works
"""

from __future__ import annotations

from agentic_fleet.utils.cosmos import (
    get_default_user_id,
    get_execution,
    is_cosmos_enabled,
    load_execution_history,
    mirror_cache_entry,
    mirror_dspy_examples,
    mirror_execution_history,
    query_agent_memory,
    record_dspy_optimization_run,
    save_agent_memory_item,
)
from agentic_fleet.utils.history_manager import HistoryManager
from agentic_fleet.utils.job_store import InMemoryJobStore, JobStore
from agentic_fleet.utils.persistence import (
    ConversationPersistenceService,
    DatabaseManager,
    PersistenceSettings,
)

__all__ = [
    "ConversationPersistenceService",
    "DatabaseManager",
    "HistoryManager",
    "InMemoryJobStore",
    "JobStore",
    "PersistenceSettings",
    "get_default_user_id",
    "get_execution",
    "is_cosmos_enabled",
    "load_execution_history",
    "mirror_cache_entry",
    "mirror_dspy_examples",
    "mirror_execution_history",
    "query_agent_memory",
    "record_dspy_optimization_run",
    "save_agent_memory_item",
]
