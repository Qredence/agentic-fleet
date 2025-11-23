import time

import pytest

from agentic_fleet.utils.cache import TTLCache, cache_agent_response


def test_ttlcache_expires_and_tracks_stats():
    cache = TTLCache(ttl_seconds=0.05)
    cache.set("k", "v")
    assert cache.get("k") == "v"

    time.sleep(0.06)  # allow entry to expire and cleanup interval to elapse
    assert cache.get("k") is None

    stats = cache.get_stats()
    assert stats.hits == 1
    # One miss when expired entry was seen, and one when not found after removal
    assert stats.misses >= 1
    assert stats.evictions >= 1


def test_ttlcache_evicts_oldest_when_max_size_reached():
    cache = TTLCache(ttl_seconds=10, max_size=1)
    cache.set("first", 1)
    cache.set("second", 2)

    # Oldest entry should be evicted
    assert cache.get("first") is None
    assert cache.get("second") == 2
    assert cache.get_stats().evictions == 1


@pytest.mark.asyncio
async def test_cache_agent_response_caches_by_task_and_agent(monkeypatch):
    calls: list[str] = []

    class DummyAgent:
        name = "TestAgent"

        @cache_agent_response(ttl=1)
        async def run_cached(self, task: str):
            calls.append(task)
            return f"done:{task}"

    agent = DummyAgent()

    result1 = await agent.run_cached("task-1")
    result2 = await agent.run_cached("task-1")

    assert result1 == "done:task-1"
    assert result2 == "done:task-1"
    # Underlying function should have been called only once thanks to cache
    assert calls == ["task-1"]
