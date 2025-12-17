"""Tests for Phase 4 TTL cache utilities."""

import asyncio
import time

import pytest

from agentic_fleet.utils.ttl_cache import AsyncTTLCache, CacheStats, SyncTTLCache


class TestSyncTTLCache:
    """Tests for synchronous TTL cache."""

    def test_basic_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = SyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = SyncTTLCache[str, str](ttl_seconds=0.05, max_size=100)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.06)
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        """Test LRU eviction when max_size is reached."""
        cache = SyncTTLCache[str, int](ttl_seconds=10, max_size=2)

        cache.set("key1", 1)
        cache.set("key2", 2)
        cache.set("key3", 3)  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == 2
        assert cache.get("key3") == 3

    def test_lru_ordering(self):
        """Test that recently accessed items are not evicted."""
        cache = SyncTTLCache[str, int](ttl_seconds=10, max_size=2)

        cache.set("key1", 1)
        cache.set("key2", 2)

        # Access key1 to make it recently used
        _ = cache.get("key1")

        # Add key3 - should evict key2, not key1
        cache.set("key3", 3)

        assert cache.get("key1") == 1
        assert cache.get("key2") is None
        assert cache.get("key3") == 3

    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = SyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()

        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.size == 1

    def test_invalidate(self):
        """Test manual cache invalidation."""
        cache = SyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        result = cache.invalidate("key1")
        assert result is True
        assert cache.get("key1") is None

        # Invalidating non-existent key
        result = cache.invalidate("key2")
        assert result is False

    def test_clear(self):
        """Test clearing entire cache."""
        cache = SyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

        stats = cache.get_stats()
        assert stats.size == 0

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = SyncTTLCache[str, str](ttl_seconds=0.05, max_size=100)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Wait for expiration
        time.sleep(0.06)

        removed = cache.cleanup_expired()

        assert removed == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_update_existing_key(self):
        """Test updating an existing key."""
        cache = SyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        cache.set("key1", "value1")
        cache.set("key1", "value2")

        assert cache.get("key1") == "value2"

        stats = cache.get_stats()
        assert stats.size == 1  # Should not grow

    def test_eviction_stats(self):
        """Test eviction statistics tracking."""
        cache = SyncTTLCache[str, int](ttl_seconds=10, max_size=1)

        cache.set("key1", 1)
        cache.set("key2", 2)  # Should evict key1

        stats = cache.get_stats()
        assert stats.evictions >= 1


@pytest.mark.asyncio
class TestAsyncTTLCache:
    """Tests for asynchronous TTL cache."""

    async def test_basic_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = AsyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        await cache.set("key1", "value1")
        result = await cache.get("key1")

        assert result == "value1"

    async def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = AsyncTTLCache[str, str](ttl_seconds=0.05, max_size=100)

        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"

        # Wait for expiration
        await asyncio.sleep(0.06)
        assert await cache.get("key1") is None

    async def test_lru_eviction(self):
        """Test LRU eviction when max_size is reached."""
        cache = AsyncTTLCache[str, int](ttl_seconds=10, max_size=2)

        await cache.set("key1", 1)
        await cache.set("key2", 2)
        await cache.set("key3", 3)  # Should evict key1

        assert await cache.get("key1") is None
        assert await cache.get("key2") == 2
        assert await cache.get("key3") == 3

    async def test_concurrent_access(self):
        """Test concurrent cache access with asyncio."""
        cache = AsyncTTLCache[str, int](ttl_seconds=10, max_size=100)

        async def writer(key: str, value: int):
            await cache.set(key, value)

        async def reader(key: str) -> int | None:
            return await cache.get(key)

        # Concurrent writes
        await asyncio.gather(
            writer("key1", 1),
            writer("key2", 2),
            writer("key3", 3),
        )

        # Concurrent reads
        results = await asyncio.gather(
            reader("key1"),
            reader("key2"),
            reader("key3"),
        )

        assert results == [1, 2, 3]

    async def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = AsyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Miss

        stats = await cache.get_stats()

        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.size == 1

    async def test_invalidate(self):
        """Test manual cache invalidation."""
        cache = AsyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"

        result = await cache.invalidate("key1")
        assert result is True
        assert await cache.get("key1") is None

    async def test_clear(self):
        """Test clearing entire cache."""
        cache = AsyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        await cache.clear()

        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    async def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = AsyncTTLCache[str, str](ttl_seconds=0.05, max_size=100)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Wait for expiration
        await asyncio.sleep(0.06)

        removed = await cache.cleanup_expired()

        assert removed == 2
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    async def test_conversation_isolation(self):
        """Test cache key isolation for different conversations."""
        cache = AsyncTTLCache[str, dict](ttl_seconds=10, max_size=100)

        # Simulate different conversation contexts
        conv1_key = "conv1:task1:context1"
        conv2_key = "conv2:task1:context1"

        await cache.set(conv1_key, {"result": "conv1_result"})
        await cache.set(conv2_key, {"result": "conv2_result"})

        result1 = await cache.get(conv1_key)
        result2 = await cache.get(conv2_key)

        assert result1 == {"result": "conv1_result"}
        assert result2 == {"result": "conv2_result"}

        # Ensure no cross-contamination
        assert result1 != result2


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_stats_creation(self):
        """Test CacheStats creation."""
        stats = CacheStats(hits=10, misses=5, evictions=2, size=50)

        assert stats.hits == 10
        assert stats.misses == 5
        assert stats.evictions == 2
        assert stats.size == 50

    def test_stats_defaults(self):
        """Test CacheStats default values."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size == 0
