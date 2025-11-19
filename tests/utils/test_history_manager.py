"""Tests for history manager utility."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_fleet.utils.history_manager import HistoryManager


@pytest.fixture(autouse=True)
def mock_cosmos_disabled():
    """Disable Cosmos DB for all tests in this module."""
    with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
        yield


def test_history_manager_jsonl_format(tmp_path):
    """Test JSONL format saves correctly."""
    manager = HistoryManager(history_format="jsonl")
    manager.history_dir = tmp_path

    execution = {"task": "test", "result": "success", "timestamp": "2024-01-01"}
    file_path = manager.save_execution(execution)

    assert Path(file_path).exists()
    assert file_path.endswith(".jsonl")

    # Verify content
    with open(file_path) as f:
        lines = f.readlines()
        assert len(lines) == 1
        loaded = json.loads(lines[0])
        assert loaded == execution


def test_history_manager_json_format(tmp_path):
    """Test JSON format saves correctly."""
    manager = HistoryManager(history_format="json")
    manager.history_dir = tmp_path

    execution1 = {"task": "test1", "result": "success1"}
    execution2 = {"task": "test2", "result": "success2"}

    file_path1 = manager.save_execution(execution1)
    file_path2 = manager.save_execution(execution2)

    assert file_path1 == file_path2  # Same file
    assert file_path1.endswith(".json")

    # Verify both executions are in the file
    with open(file_path1) as f:
        loaded = json.load(f)
        assert len(loaded) == 2
        assert loaded[0] == execution1
        assert loaded[1] == execution2


def test_history_manager_load_jsonl(tmp_path):
    """Test loading JSONL history."""
    manager = HistoryManager(history_format="jsonl")
    manager.history_dir = tmp_path

    # Create test file
    test_file = tmp_path / "execution_history.jsonl"
    with open(test_file, "w") as f:
        json.dump({"task": "test1"}, f)
        f.write("\n")
        json.dump({"task": "test2"}, f)
        f.write("\n")

    history = manager.load_history()
    assert len(history) == 2
    assert history[0]["task"] == "test1"
    assert history[1]["task"] == "test2"


def test_history_manager_load_json(tmp_path):
    """Test loading JSON history."""
    manager = HistoryManager(history_format="json")
    manager.history_dir = tmp_path

    # Create test file
    test_file = tmp_path / "execution_history.json"
    with open(test_file, "w") as f:
        json.dump([{"task": "test1"}, {"task": "test2"}], f)

    history = manager.load_history()
    assert len(history) == 2
    assert history[0]["task"] == "test1"
    assert history[1]["task"] == "test2"


def test_history_manager_load_with_limit(tmp_path):
    """Test loading history with limit."""
    manager = HistoryManager(history_format="jsonl")
    manager.history_dir = tmp_path

    # Create test file with 5 entries
    test_file = tmp_path / "execution_history.jsonl"
    with open(test_file, "w") as f:
        for i in range(5):
            json.dump({"task": f"test{i}"}, f)
            f.write("\n")

    # Load last 2 entries
    history = manager.load_history(limit=2)
    assert len(history) == 2
    assert history[0]["task"] == "test3"
    assert history[1]["task"] == "test4"


def test_history_manager_rotation_jsonl(tmp_path):
    """Test JSONL rotation keeps only last N entries."""
    manager = HistoryManager(history_format="jsonl", max_entries=3)
    manager.history_dir = tmp_path

    # Add 5 executions
    for i in range(5):
        manager.save_execution({"task": f"test{i}", "index": i})

    # Verify only last 3 remain
    history = manager.load_history()
    assert len(history) == 3
    assert history[0]["index"] == 2
    assert history[1]["index"] == 3
    assert history[2]["index"] == 4


def test_history_manager_rotation_json(tmp_path):
    """Test JSON rotation keeps only last N entries."""
    manager = HistoryManager(history_format="json", max_entries=3)
    manager.history_dir = tmp_path

    # Add 5 executions
    for i in range(5):
        manager.save_execution({"task": f"test{i}", "index": i})

    # Verify only last 3 remain
    history = manager.load_history()
    assert len(history) == 3
    assert history[0]["index"] == 2
    assert history[1]["index"] == 3
    assert history[2]["index"] == 4


def test_history_manager_clear_history(tmp_path):
    """Test clearing history."""
    manager = HistoryManager(history_format="jsonl")
    manager.history_dir = tmp_path

    # Add some executions
    manager.save_execution({"task": "test1"})
    manager.save_execution({"task": "test2"})

    # Clear all
    manager.clear_history(keep_recent=0)
    assert len(manager.load_history()) == 0

    # Add again and clear keeping recent
    manager.save_execution({"task": "test3"})
    manager.save_execution({"task": "test4"})
    manager.clear_history(keep_recent=1)

    history = manager.load_history()
    assert len(history) == 1
    assert history[0]["task"] == "test4"


def test_history_manager_get_stats(tmp_path):
    """Test getting history statistics."""
    manager = HistoryManager(history_format="jsonl")
    manager.history_dir = tmp_path

    # Add executions with timing data
    manager.save_execution({"task": "test1", "total_time_seconds": 1.5})
    manager.save_execution({"task": "test2", "total_time_seconds": 2.5})
    manager.save_execution({"task": "test3", "total_time_seconds": 3.0, "quality": {"score": 8.0}})

    stats = manager.get_history_stats()
    assert stats["total_executions"] == 3
    assert stats["total_time_seconds"] == 7.0
    assert stats["average_time_seconds"] == pytest.approx(7.0 / 3)
    assert stats["average_quality_score"] == 8.0
    assert stats["format"] == "jsonl"


@pytest.mark.asyncio
async def test_history_manager_async_save_jsonl(tmp_path):
    """Test async JSONL save."""
    manager = HistoryManager(history_format="jsonl")
    manager.history_dir = tmp_path

    execution = {"task": "async_test", "result": "success"}
    file_path = await manager.save_execution_async(execution)

    assert Path(file_path).exists()
    history = manager.load_history()
    assert len(history) == 1
    assert history[0] == execution


@pytest.mark.asyncio
async def test_history_manager_async_save_json(tmp_path):
    """Test async JSON save."""
    manager = HistoryManager(history_format="json")
    manager.history_dir = tmp_path

    execution = {"task": "async_test", "result": "success"}
    file_path = await manager.save_execution_async(execution)

    assert Path(file_path).exists()
    history = manager.load_history()
    assert len(history) == 1
    assert history[0] == execution
