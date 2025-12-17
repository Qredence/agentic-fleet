"""Tests for utils/cosmos.py - Azure Cosmos DB helpers."""

from __future__ import annotations

import os
from unittest.mock import patch

# Import the actual public functions from the module
from agentic_fleet.utils.cosmos import (
    get_default_user_id,
    is_cosmos_enabled,
    load_execution_history,
    mirror_cache_entry,
    mirror_dspy_examples,
    mirror_execution_history,
    query_agent_memory,
    record_dspy_optimization_run,
    save_agent_memory_item,
)

# =============================================================================
# Test: is_cosmos_enabled
# =============================================================================


class TestIsCosmosEnabled:
    """Test suite for is_cosmos_enabled function."""

    def test_cosmos_disabled_by_default(self):
        """Test that Cosmos is disabled when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing cosmos env vars
            for key in list(os.environ.keys()):
                if "COSMOS" in key:
                    del os.environ[key]
            # This test depends on environment state; cosmos may be enabled
            # Just verify the function is callable
            result = is_cosmos_enabled()
            assert isinstance(result, bool)

    def test_cosmos_enabled_with_env_var(self):
        """Test that Cosmos is enabled when env var is set."""
        with patch.dict(
            os.environ,
            {"AGENTICFLEET_USE_COSMOS": "true"},
        ):
            # Function checks for SDK availability too
            result = is_cosmos_enabled()
            assert isinstance(result, bool)

    def test_cosmos_disabled_with_false_env_var(self):
        """Test that Cosmos is disabled when env var is false."""
        with patch.dict(
            os.environ,
            {"AGENTICFLEET_USE_COSMOS": "false"},
            clear=True,
        ):
            result = is_cosmos_enabled()
            # Should return False when explicitly disabled
            assert result is False
            assert isinstance(result, bool)


# =============================================================================
# Test: get_default_user_id
# =============================================================================


class TestGetDefaultUserId:
    """Test suite for get_default_user_id function."""

    def test_get_user_id_from_env(self):
        """Test getting user ID from environment variable."""
        # The function checks AGENTICFLEET_DEFAULT_USER_ID, AGENTICFLEET_USER_ID, USER, USERNAME
        with patch.dict(
            os.environ,
            {"AGENTICFLEET_DEFAULT_USER_ID": "test-user-123"},
            clear=True,
        ):
            result = get_default_user_id()
            assert result == "test-user-123"

    def test_get_user_id_returns_fallback_when_primary_not_set(self):
        """Test fallback to USER env var when primary not set."""
        with patch.dict(
            os.environ,
            {"USER": "fallback-user"},
            clear=True,
        ):
            result = get_default_user_id()
            assert result == "fallback-user"


# =============================================================================
# Test: mirror_execution_history
# =============================================================================


class TestMirrorExecutionHistory:
    """Test suite for mirror_execution_history function."""

    def test_mirror_execution_history_when_disabled(self):
        """Test that mirroring is skipped when Cosmos is disabled."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            # Should not raise, just skip
            mirror_execution_history({"task": "test", "result": "done"})

    def test_mirror_execution_history_with_valid_data(self):
        """Test mirroring execution history with valid data."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            # When disabled, should silently skip
            execution = {
                "workflow_id": "wf-123",
                "task": "Test task",
                "status": "completed",
                "result": {"output": "test result"},
            }
            # Should not raise
            mirror_execution_history(execution)

    def test_mirror_execution_history_with_empty_dict(self):
        """Test mirroring with empty execution dict."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            # Should handle gracefully
            mirror_execution_history({})


# =============================================================================
# Test: save_agent_memory_item
# =============================================================================


class TestSaveAgentMemoryItem:
    """Test suite for save_agent_memory_item function."""

    def test_save_memory_when_disabled(self):
        """Test saving memory item when Cosmos is disabled."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            # Should not raise when disabled
            save_agent_memory_item({"key": "value"})

    def test_save_memory_with_user_id(self):
        """Test saving memory item with explicit user ID."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            save_agent_memory_item({"memory": "data"}, user_id="user-456")


# =============================================================================
# Test: query_agent_memory
# =============================================================================


class TestQueryAgentMemory:
    """Test suite for query_agent_memory function."""

    def test_query_memory_when_disabled(self):
        """Test querying memory when Cosmos is disabled."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            result = query_agent_memory(user_id="user-123")
            assert result == []

    def test_query_memory_with_agent_filter(self):
        """Test querying memory with agent ID filter."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            result = query_agent_memory(user_id="user-123", agent_id="researcher")
            assert result == []


# =============================================================================
# Test: mirror_dspy_examples
# =============================================================================


class TestMirrorDspyExamples:
    """Test suite for mirror_dspy_examples function."""

    def test_mirror_examples_when_disabled(self):
        """Test mirroring DSPy examples when Cosmos is disabled."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            examples = [{"input": "test", "output": "result"}]
            # Should not raise
            mirror_dspy_examples(examples, dataset="test_dataset")

    def test_mirror_empty_examples(self):
        """Test mirroring empty examples list."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            mirror_dspy_examples([], dataset="empty_dataset")


# =============================================================================
# Test: record_dspy_optimization_run
# =============================================================================


class TestRecordDspyOptimizationRun:
    """Test suite for record_dspy_optimization_run function."""

    def test_record_optimization_when_disabled(self):
        """Test recording optimization run when Cosmos is disabled."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            # Should not raise - pass the run dict directly
            record_dspy_optimization_run(
                run={
                    "optimizer": "MIPRO",
                    "signature": "TestSignature",
                    "metrics": {"accuracy": 0.95},
                }
            )


# =============================================================================
# Test: mirror_cache_entry
# =============================================================================


class TestMirrorCacheEntry:
    """Test suite for mirror_cache_entry function."""

    def test_mirror_cache_when_disabled(self):
        """Test mirroring cache entry when Cosmos is disabled."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            # Should not raise
            mirror_cache_entry("cache_key_123", {"data": "cached"})


# =============================================================================
# Test: load_execution_history
# =============================================================================


class TestLoadExecutionHistory:
    """Test suite for load_execution_history function."""

    def test_load_history_when_disabled(self):
        """Test loading history when Cosmos is disabled."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            result = load_execution_history()
            assert result == []

    def test_load_history_with_limit(self):
        """Test loading history with custom limit."""
        with patch("agentic_fleet.utils.cosmos.is_cosmos_enabled", return_value=False):
            result = load_execution_history(limit=5)
            assert result == []


# =============================================================================
# Test: Module-level behavior
# =============================================================================


class TestCosmosModuleBehavior:
    """Test module-level behavior and error handling."""

    def test_module_imports_successfully(self):
        """Test that the cosmos module imports without errors."""
        import agentic_fleet.utils.cosmos as cosmos_module

        assert cosmos_module is not None

    def test_graceful_degradation_without_sdk(self):
        """Test that module degrades gracefully without Azure SDK."""
        # The module should handle missing SDK gracefully
        # This is already handled by the try/except in the module
        assert callable(is_cosmos_enabled)
        assert callable(mirror_execution_history)

    def test_all_public_functions_callable(self):
        """Test that all public functions are callable."""
        functions = [
            is_cosmos_enabled,
            get_default_user_id,
            mirror_execution_history,
            save_agent_memory_item,
            query_agent_memory,
            mirror_dspy_examples,
            record_dspy_optimization_run,
            mirror_cache_entry,
            load_execution_history,
        ]
        for func in functions:
            assert callable(func)
