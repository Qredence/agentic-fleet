"""Thread-safe TTL+LRU cache with metrics.

Phase 4: Shared async-safe cache utility for DSPy decision module caching.

Features:
- TTL (Time To Live) eviction
- LRU (Least Recently Used) eviction when max_size reached
- Asyncio lock for thread safety
- Metrics tracking (hits, misses, evictions)
- Conversation isolation via cache key prefixes
"""

from __future__ import annotations

import asyncio
import threading as _threading
import time
from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0


@dataclass
class _CacheEntry[V]:
    """Internal cache entry with TTL tracking."""

    value: V
    expires_at: float


class AsyncTTLCache[K, V]:
    """Async-safe TTL+LRU cache with metrics.

    This cache combines TTL-based expiration with LRU eviction when
    the cache reaches max_size. All operations are protected by an
    asyncio lock for thread safety.

    Example:
        cache = AsyncTTLCache[str, dict](ttl_seconds=300, max_size=1000)

        async def get_routing_decision(task: str, context: str):
            key = f"{task}:{context}"
            result = await cache.get(key)
            if result is None:
                result = await compute_routing(task, context)
                await cache.set(key, result)
            return result
    """

    def __init__(
        self,
        ttl_seconds: float = 300,
        max_size: int = 1000,
    ) -> None:
        """Initialize async TTL cache.

        Args:
            ttl_seconds: Time to live for cache entries in seconds
            max_size: Maximum number of entries before LRU eviction
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: OrderedDict[K, _CacheEntry[V]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = CacheStats()

    async def get(self, key: K) -> V | None:
        """Get value from cache if present and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            # Check if expired
            if time.time() >= entry.expires_at:
                self._cache.pop(key)
                self._stats.misses += 1
                self._stats.evictions += 1
                return None

            # Move to end (mark as recently used for LRU)
            self._cache.move_to_end(key)
            self._stats.hits += 1
            return entry.value

    async def set(self, key: K, value: V) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
        """
        async with self._lock:
            expires_at = time.time() + self.ttl_seconds
            entry = _CacheEntry(value=value, expires_at=expires_at)

            # If key exists, update it
            if key in self._cache:
                self._cache[key] = entry
                self._cache.move_to_end(key)
                return

            # Check if we need to evict LRU entry
            if len(self._cache) >= self.max_size:
                # Remove oldest entry (FIFO from OrderedDict)
                self._cache.popitem(last=False)
                self._stats.evictions += 1

            self._cache[key] = entry
            self._stats.size = len(self._cache)

    async def invalidate(self, key: K) -> bool:
        """Remove entry from cache.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was present, False otherwise
        """
        async with self._lock:
            if key in self._cache:
                self._cache.pop(key)
                self._stats.size = len(self._cache)
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries from cache."""
        async with self._lock:
            self._cache.clear()
            self._stats.size = 0

    async def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Current cache statistics
        """
        async with self._lock:
            self._stats.size = len(self._cache)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=self._stats.size,
            )

    async def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            now = time.time()
            expired_keys = [k for k, v in self._cache.items() if now >= v.expires_at]

            for key in expired_keys:
                self._cache.pop(key)
                self._stats.evictions += 1

            self._stats.size = len(self._cache)
            return len(expired_keys)


class SyncTTLCache[K, V]:
    """Synchronous TTL+LRU cache with metrics.

    Same functionality as AsyncTTLCache but for synchronous code.
    Uses threading.Lock instead of asyncio.Lock.
    """

    def __init__(
        self,
        ttl_seconds: float = 300,
        max_size: int = 1000,
    ) -> None:
        """Initialize sync TTL cache.

        Args:
            ttl_seconds: Time to live for cache entries in seconds
            max_size: Maximum number of entries before LRU eviction
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: OrderedDict[K, _CacheEntry[V]] = OrderedDict()
        self._lock = _threading.Lock()
        self._stats = CacheStats()

    def get(self, key: K) -> V | None:
        """Get value from cache if present and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            # Check if expired
            if time.time() >= entry.expires_at:
                self._cache.pop(key)
                self._stats.misses += 1
                self._stats.evictions += 1
                return None

            # Move to end (mark as recently used for LRU)
            self._cache.move_to_end(key)
            self._stats.hits += 1
            return entry.value

    def set(self, key: K, value: V) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            expires_at = time.time() + self.ttl_seconds
            entry = _CacheEntry(value=value, expires_at=expires_at)

            # If key exists, update it
            if key in self._cache:
                self._cache[key] = entry
                self._cache.move_to_end(key)
                return

            # Check if we need to evict LRU entry
            if len(self._cache) >= self.max_size:
                # Remove oldest entry (FIFO from OrderedDict)
                self._cache.popitem(last=False)
                self._stats.evictions += 1

            self._cache[key] = entry
            self._stats.size = len(self._cache)

    def invalidate(self, key: K) -> bool:
        """Remove entry from cache.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was present, False otherwise
        """
        with self._lock:
            if key in self._cache:
                self._cache.pop(key)
                self._stats.size = len(self._cache)
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._stats.size = 0

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Current cache statistics
        """
        with self._lock:
            self._stats.size = len(self._cache)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=self._stats.size,
            )

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            expired_keys = [k for k, v in self._cache.items() if now >= v.expires_at]

            for key in expired_keys:
                self._cache.pop(key)
                self._stats.evictions += 1

            self._stats.size = len(self._cache)
            return len(expired_keys)


__all__ = [
    "AsyncTTLCache",
    "CacheStats",
    "SyncTTLCache",
]
