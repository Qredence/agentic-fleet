"""Integration tests for Phase 3 and Phase 4 enhancements."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.dspy_modules.compiled_registry import (
    ArtifactMetadata,
    load_required_compiled_modules,
)


class TestPhase3Integration:
    """Integration tests for Phase 3 fail-fast and metadata validation."""

    def test_backward_compatibility_with_require_compiled_false(self, tmp_path):
        """Test that missing artifacts don't fail when require_compiled=false."""
        # This simulates dev mode where artifacts may not exist yet
        dspy_config = {
            "compiled_routing_path": str(tmp_path / "nonexistent_routing.json"),
            "compiled_tool_planning_path": str(tmp_path / "nonexistent_tool_planning.json"),
            "compiled_quality_path": str(tmp_path / "nonexistent_quality.pkl"),
        }

        # Should not raise with require_compiled=False
        registry = load_required_compiled_modules(
            dspy_config=dspy_config,
            require_compiled=False,
        )

        assert registry is not None
        # All modules should be None (not loaded)
        assert registry.routing is None
        assert registry.tool_planning is None
        assert registry.quality is None

    def test_fail_fast_with_require_compiled_true(self, tmp_path):
        """Test that missing artifacts fail fast in production mode."""
        routing_path = tmp_path / "nonexistent_routing.json"
        tool_planning_path = tmp_path / "nonexistent_tool_planning.json"
        quality_path = tmp_path / "nonexistent_quality.pkl"

        # Verify files don't exist
        assert not routing_path.exists()
        assert not tool_planning_path.exists()
        assert not quality_path.exists()

        dspy_config = {
            "compiled_routing_path": str(routing_path),
            "compiled_tool_planning_path": str(tool_planning_path),
            "compiled_quality_path": str(quality_path),
        }

        # Should raise RuntimeError with require_compiled=True
        with pytest.raises(RuntimeError) as exc_info:
            load_required_compiled_modules(
                dspy_config=dspy_config,
                require_compiled=True,
            )

        error_msg = str(exc_info.value)
        # Should have actionable error message
        assert "Missing required artifacts" in error_msg
        assert "agentic-fleet optimize" in error_msg
        assert "dspy.require_compiled: false" in error_msg

    @patch("agentic_fleet.utils.compiler.load_compiled_module")
    @patch("agentic_fleet.dspy_modules.compiled_registry._resolve_artifact_path")
    @patch("agentic_fleet.dspy_modules.compiled_registry._load_artifact_metadata")
    def test_metadata_captured_in_registry(self, mock_load_meta, mock_resolve, mock_load, tmp_path):
        """Test that artifact metadata is properly captured."""
        # Create artifact files
        artifact_path = tmp_path / "test_routing.json"
        artifact_path.touch()

        # Mock path resolution - return actual path that exists
        def resolve_side_effect(path):
            result = tmp_path / Path(path).name
            result.touch()
            return result

        mock_resolve.side_effect = resolve_side_effect

        # Mock metadata loading
        metadata = ArtifactMetadata(
            schema_version=3,
            dspy_version="3.0.5",
            created_at="2024-01-01T00:00:00",
            optimizer="gepa",
            serializer="pickle",
        )
        mock_load_meta.return_value = metadata

        # Mock module loading
        mock_module = MagicMock()
        mock_load.return_value = mock_module

        dspy_config = {
            "compiled_routing_path": str(artifact_path),
            "compiled_tool_planning_path": str(tmp_path / "tool_planning.json"),
            "compiled_quality_path": str(tmp_path / "quality.pkl"),
        }

        # Load with metadata
        registry = load_required_compiled_modules(
            dspy_config=dspy_config,
            require_compiled=False,
        )

        # Verify module was loaded
        assert registry.routing is mock_module


class TestPhase4Integration:
    """Integration tests for Phase 4 caching and parallel compilation."""

    @pytest.mark.asyncio
    async def test_ttl_cache_conversation_isolation(self):
        """Test that cache properly isolates different conversations."""
        from agentic_fleet.utils.ttl_cache import AsyncTTLCache

        cache = AsyncTTLCache[str, dict](ttl_seconds=10, max_size=100)

        # Simulate routing decisions for different conversations
        conv1_key = "conv_123:task:analyze data:model:gpt-4"
        conv2_key = "conv_456:task:analyze data:model:gpt-4"

        await cache.set(conv1_key, {"agent": "analyst", "confidence": 0.9})
        await cache.set(conv2_key, {"agent": "researcher", "confidence": 0.8})

        # Retrieve and verify isolation
        result1 = await cache.get(conv1_key)
        result2 = await cache.get(conv2_key)

        assert result1 is not None
        assert result2 is not None
        assert result1["agent"] == "analyst"
        assert result2["agent"] == "researcher"

        # Invalidate one conversation shouldn't affect the other
        await cache.invalidate(conv1_key)
        assert await cache.get(conv1_key) is None
        assert await cache.get(conv2_key) is not None

    def test_parallel_compilation_flag(self):
        """Test that parallel compilation flag is properly handled."""
        from agentic_fleet.models.dspy import CompileRequest
        from agentic_fleet.services.optimization_jobs import _compile_all

        # Mock workflow
        mock_workflow = MagicMock()
        mock_workflow.dspy_reasoner = MagicMock()
        mock_workflow.config.dspy_model = "gpt-4"
        mock_workflow.config.dspy_temperature = 1.0
        mock_workflow.config.dspy_max_tokens = 16000
        mock_workflow.config.examples_path = "test_examples.json"

        request = CompileRequest(
            optimizer="bootstrap",
            use_cache=True,
        )

        # Mock progress callback
        mock_callback = MagicMock()

        # Patch all compilation functions
        with (
            patch("agentic_fleet.services.optimization_jobs.compile_reasoner") as mock_reasoner,
            patch(
                "agentic_fleet.services.optimization_jobs.compile_answer_quality"
            ) as mock_quality,
            patch("agentic_fleet.services.optimization_jobs.compile_nlu") as mock_nlu,
        ):
            mock_reasoner.return_value = MagicMock()
            mock_quality.return_value = MagicMock()
            mock_nlu.return_value = MagicMock()

            # Test parallel=True
            result = _compile_all(mock_workflow, request, mock_callback, parallel=True)

            # Verify all modules were compiled
            assert "cache_paths" in result
            assert "supervisor" in result["cache_paths"]
            assert "answer_quality" in result["cache_paths"]
            assert "nlu" in result["cache_paths"]

            # Test parallel=False (backward compatibility)
            result = _compile_all(mock_workflow, request, mock_callback, parallel=False)
            assert "cache_paths" in result


class TestConstraintsVerification:
    """Verify that Phase 3 and 4 changes meet the constraints."""

    def test_backward_compatibility_maintained(self, tmp_path):
        """Verify backward compatibility when require_compiled=false."""
        # This is the critical test for the constraint
        dspy_config = {
            "compiled_routing_path": str(tmp_path / "missing.json"),
            "compiled_tool_planning_path": str(tmp_path / "missing.json"),
            "compiled_quality_path": str(tmp_path / "missing.pkl"),
        }

        # Should gracefully handle missing artifacts
        try:
            registry = load_required_compiled_modules(
                dspy_config=dspy_config,
                require_compiled=False,
            )
            assert registry is not None
        except Exception as e:
            pytest.fail(
                f"Backward compatibility broken: {e}. "
                "Should allow missing artifacts when require_compiled=False"
            )

    @pytest.mark.asyncio
    async def test_cache_operations_do_not_block(self):
        """Verify that cache operations are async-safe and don't block."""
        import asyncio

        from agentic_fleet.utils.ttl_cache import AsyncTTLCache

        cache = AsyncTTLCache[str, str](ttl_seconds=10, max_size=100)

        # Simulate concurrent cache operations
        async def writer(key: str, value: str):
            await cache.set(key, value)
            await asyncio.sleep(0.001)  # Simulate some work

        async def reader(key: str):
            return await cache.get(key)

        # Run many concurrent operations
        loop = asyncio.get_running_loop()
        start = loop.time()
        await asyncio.gather(
            *[writer(f"key{i}", f"value{i}") for i in range(100)],
            *[reader(f"key{i}") for i in range(100)],
        )
        elapsed = loop.time() - start

        # Should complete quickly (under 1 second for 200 operations)
        assert elapsed < 1.0, "Cache operations should not block significantly"
