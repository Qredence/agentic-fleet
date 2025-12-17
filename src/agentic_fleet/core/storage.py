"""Core storage utilities for AgenticFleet.

This module provides unified storage and persistence capabilities, consolidating:
- Conversation store (from app/conversation_store.py)
- History management (from utils/history_manager.py)
- TTL cache utilities (from utils/cache.py)

Usage:
    from agentic_fleet.core.storage import (
        ConversationStore,
        HistoryManager,
        TTLCache,
        cache_agent_response,
    )

    # Conversation storage
    store = ConversationStore()
    conversations = store.list_conversations()

    # History management
    history = HistoryManager()
    history.save_execution({"workflowId": "wf-123", ...})

    # TTL cache
    cache = TTLCache[str, dict](ttl_seconds=300)
    cache.set("key", {"value": 42})
"""

from __future__ import annotations

from agentic_fleet.core.conversation_store import ConversationStore
from agentic_fleet.utils.cache import (
    CacheStats,
    TTLCache,
    cache_agent_response,
)
from agentic_fleet.utils.history_manager import (
    FleetJSONEncoder,
    HistoryManager,
)

__all__ = [
    "CacheStats",
    "ConversationStore",
    "FleetJSONEncoder",
    "HistoryManager",
    "TTLCache",
    "cache_agent_response",
]
