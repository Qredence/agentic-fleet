"""
Simple in-memory caching utilities with TTL support and hit rate metrics.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, TypeVar

from .cfg import DEFAULT_CACHE_TTL
from .cosmos import mirror_cache_entry
from .logger import setup_logger

logger = setup_logger(__name__)


K = TypeVar("K")
V = TypeVar("V")


@dataclass
class _CacheEntry[V]:
    """Internal cache entry with expiration tracking."""

    value: V
    expires_at: float
    created_at: float = field(default_factory=time.time)


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    sets: int = 0

    @property
    def total_requests(self) -> int:
        """Total cache requests (hits + misses)."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    def reset(self) -> None:
        """Reset all statistics."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.sets = 0


class TTLCache[K, V]:
    """A lightweight in-memory cache with time-to-live semantics and metrics.

    Features:
    - Automatic expiration of entries
    - Hit rate tracking
    - Statistics for monitoring
    - Incremental cleanup of expired entries
    """

    def __init__(self, ttl_seconds: float = DEFAULT_CACHE_TTL, max_size: int | None = None):
        """Initialize TTL cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
            max_size: Maximum number of entries (None for unlimited)
        """
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl = float(ttl_seconds)
        self._max_size = max_size
        self._store: dict[K, _CacheEntry[V]] = {}
        self._stats = CacheStats()
        self._last_cleanup = time.time()
        self._cleanup_interval = min(
            ttl_seconds / 10, 60
        )  # Clean up every 10% of TTL or 60s, whichever is less

    def get(self, key: K) -> V | None:
        """Retrieve a cached value if it exists and hasn't expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        # Periodic cleanup of expired entries
        self._cleanup_if_needed()

        entry = self._store.get(key)
        if not entry:
            self._stats.misses += 1
            return None

        if entry.expires_at < time.time():
            # Entry expired
            self._store.pop(key, None)
            self._stats.misses += 1
            self._stats.evictions += 1
            return None

        self._stats.hits += 1
        return entry.value

    def set(self, key: K, value: V) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Cleanup before adding if at max size
        if self._max_size and len(self._store) >= self._max_size:
            self._evict_oldest()

        self._store[key] = _CacheEntry(
            value=value, expires_at=time.time() + self._ttl, created_at=time.time()
        )
        self._stats.sets += 1

    def delete(self, key: K) -> None:
        """Delete a specific cache entry.

        Args:
            key: Cache key to delete
        """
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()
        self._stats.reset()

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats object with current metrics
        """
        return self._stats

    def _cleanup_if_needed(self) -> None:
        """Clean up expired entries if cleanup interval has passed."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._cleanup_expired()
        self._last_cleanup = now

    def _cleanup_expired(self) -> None:
        """Remove all expired entries from the cache."""
        now = time.time()
        expired_keys = [key for key, entry in self._store.items() if entry.expires_at < now]
        for key in expired_keys:
            del self._store[key]
            self._stats.evictions += 1

    def _evict_oldest(self) -> None:
        """Evict the oldest entry when cache is full."""
        if not self._store:
            return

        # Find oldest entry by creation time
        oldest_key = min(self._store.keys(), key=lambda k: self._store[k].created_at)
        del self._store[oldest_key]
        self._stats.evictions += 1


# Global cache instance for agent responses
_agent_response_cache: TTLCache[str, Any] = TTLCache(ttl_seconds=DEFAULT_CACHE_TTL)


def _truthy_env(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _capture_sensitive_for_telemetry() -> bool:
    """Return True if sensitive user inputs may be captured for telemetry.

    We intentionally require an explicit opt-in via environment variables.
    This mirrors the tracing module's conventions.
    """

    return (
        _truthy_env("ENABLE_SENSITIVE_DATA")
        or _truthy_env("TRACING_SENSITIVE_DATA")
        or _truthy_env("AGENTICFLEET_CAPTURE_SENSITIVE")
    )


def cache_agent_response(
    ttl: int = DEFAULT_CACHE_TTL,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for caching agent responses.

    Args:
        ttl: Time-to-live in seconds for cached responses

    Usage:
        @cache_agent_response(ttl=300)
        async def run_cached(self, task: str) -> ChatMessage:
            return await self.execute(task)
    """
    cache: TTLCache[str, Any] = TTLCache(ttl_seconds=ttl)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(self: Any, task: str, *args: Any, **kwargs: Any) -> Any:
            # Generate cache key from task and agent name
            agent_name = getattr(self, "name", "unknown")
            cache_key = _generate_cache_key(task, agent_name)

            # Check cache first
            cached = cache.get(cache_key)
            if cached is not None:
                import logging

                logging.getLogger(__name__).debug(f"Cache hit for {agent_name}: {task[:50]}...")
                return cached

            # Execute and cache
            result = await func(self, task, *args, **kwargs)
            cache.set(cache_key, result)
            try:
                payload: dict[str, Any] = {
                    "agentName": agent_name,
                    "ttlSeconds": ttl,
                    "responseType": type(result).__name__,
                    "taskLength": len(task),
                }
                if _capture_sensitive_for_telemetry():
                    payload["taskPreview"] = task[:256]
                else:
                    payload["taskPreview"] = "[redacted]"

                mirror_cache_entry(
                    cache_key,
                    payload,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Failed to mirror cache entry: %s", exc)
            return result

        return wrapper

    return decorator


def _generate_cache_key(task: str, agent_name: str) -> str:
    """Generate cache key from task and agent name.

    Args:
        task: Task string
        agent_name: Agent identifier

    Returns:
        MD5 hash as cache key
    """
    content = f"{task}:{agent_name}"
    # MD5 used for cache key generation, not security
    return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
