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


@pytest.mark.asyncio
async def test_cache_agent_response_redacts_task_preview_by_default(monkeypatch):
    captured: dict[str, object] = {}

    def fake_mirror(cache_key: str, entry: dict[str, object]) -> None:
        captured["cache_key"] = cache_key
        captured["entry"] = entry

    monkeypatch.delenv("ENABLE_SENSITIVE_DATA", raising=False)
    monkeypatch.delenv("TRACING_SENSITIVE_DATA", raising=False)
    monkeypatch.delenv("AGENTICFLEET_CAPTURE_SENSITIVE", raising=False)
    monkeypatch.setattr("agentic_fleet.utils.cache.mirror_cache_entry", fake_mirror)

    class DummyAgent:
        name = "TestAgent"

        @cache_agent_response(ttl=1)
        async def run_cached(self, task: str):
            return f"done:{task}"

    agent = DummyAgent()
    await agent.run_cached("super-secret-task")

    entry = captured["entry"]
    assert isinstance(entry, dict)
    assert entry.get("taskPreview") == "[redacted]"
    assert entry.get("taskLength") == len("super-secret-task")


@pytest.mark.asyncio
async def test_cache_agent_response_includes_task_preview_when_enabled(monkeypatch):
    captured: dict[str, object] = {}

    def fake_mirror(cache_key: str, entry: dict[str, object]) -> None:
        captured["cache_key"] = cache_key
        captured["entry"] = entry

    monkeypatch.setenv("ENABLE_SENSITIVE_DATA", "true")
    monkeypatch.setattr("agentic_fleet.utils.cache.mirror_cache_entry", fake_mirror)

    class DummyAgent:
        name = "TestAgent"

        @cache_agent_response(ttl=1)
        async def run_cached(self, task: str):
            return f"done:{task}"

    agent = DummyAgent()
    await agent.run_cached("hello world")

    entry = captured["entry"]
    assert isinstance(entry, dict)
    assert entry.get("taskPreview") == "hello world"
