"""
Tests for lazy compilation in SupervisorWorkflow.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow, WorkflowConfig


class TestLazyCompilation:
    """Test lazy compilation functionality."""

    @pytest.mark.asyncio
    async def test_lazy_compilation_starts_in_background(self):
        """Test that compilation starts in background during initialization."""
        config = WorkflowConfig(compile_dspy=True)
        workflow = SupervisorWorkflow(config, MagicMock())

        with patch(
            "agentic_fleet.workflows.supervisor_workflow.compile_supervisor"
        ) as mock_compile:
            mock_compile.return_value = workflow.dspy_supervisor

            await workflow.initialize(compile_dspy=True)

            # Compilation task should be created
            assert workflow._compilation_task is not None
            assert workflow._compilation_status in ("compiling", "pending")

    @pytest.mark.asyncio
    async def test_compiled_supervisor_property_waits_for_completion(self):
        """Test that compiled_supervisor property waits for background compilation."""
        config = WorkflowConfig(compile_dspy=True)
        workflow = SupervisorWorkflow(config, MagicMock())

        compiled_supervisor = MagicMock()

        with patch(
            "agentic_fleet.workflows.supervisor_workflow.compile_supervisor"
        ) as mock_compile:
            mock_compile.return_value = compiled_supervisor

            await workflow.initialize(compile_dspy=True)

            # Wait for compilation to complete
            if workflow._compilation_task:
                await workflow._compilation_task

            # Property should return compiled supervisor
            assert workflow.compiled_supervisor == compiled_supervisor

    @pytest.mark.asyncio
    async def test_compiled_supervisor_fallback_on_failure(self):
        """Test that compiled_supervisor falls back to uncompiled on failure."""
        config = WorkflowConfig(compile_dspy=True)
        workflow = SupervisorWorkflow(config, MagicMock())
        original_supervisor = workflow.dspy_supervisor

        with patch(
            "agentic_fleet.workflows.supervisor_workflow.compile_supervisor"
        ) as mock_compile:
            mock_compile.side_effect = Exception("Compilation failed")

            await workflow.initialize(compile_dspy=True)

            # Wait for compilation task
            if workflow._compilation_task:
                await workflow._compilation_task

            # Should fall back to uncompiled supervisor
            assert workflow._compilation_status == "failed"
            assert workflow.compiled_supervisor == original_supervisor

    @pytest.mark.asyncio
    async def test_compiled_supervisor_triggers_sync_compilation_if_needed(self):
        """Test that compiled_supervisor triggers sync compilation if not started."""
        config = WorkflowConfig(compile_dspy=False)
        workflow = SupervisorWorkflow(config, MagicMock())

        compiled_supervisor = MagicMock()

        with patch(
            "agentic_fleet.workflows.supervisor_workflow.compile_supervisor"
        ) as mock_compile:
            mock_compile.return_value = compiled_supervisor

            await workflow.initialize(compile_dspy=False)

            # Access property - should trigger sync compilation
            supervisor = workflow.compiled_supervisor

            # Should have triggered compilation
            assert workflow._compilation_status == "completed"
            assert supervisor == compiled_supervisor

    def test_compiled_supervisor_uses_compiled_when_available(self):
        """Test that compiled_supervisor returns compiled version when available."""
        config = WorkflowConfig()
        workflow = SupervisorWorkflow(config, MagicMock())

        compiled_supervisor = MagicMock()
        workflow._compiled_supervisor = compiled_supervisor
        workflow._compilation_status = "completed"

        assert workflow.compiled_supervisor == compiled_supervisor
