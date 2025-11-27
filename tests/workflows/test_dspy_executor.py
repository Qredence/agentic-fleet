"""Tests for DSPyExecutor in workflows/executors.py.

This module tests the generic DSPyExecutor class which allows placing
any compiled DSPy module directly into the workflow graph.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_fleet.workflows.context import SupervisorContext
from agentic_fleet.workflows.executors import DSPyExecutor

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = MagicMock()
    config.dspy_retry_attempts = 3
    config.dspy_retry_backoff_seconds = 0.1
    return config


@pytest.fixture
def mock_supervisor_context(mock_config):
    """Create a mock supervisor context."""
    context = MagicMock(spec=SupervisorContext)
    context.config = mock_config
    context.latest_phase_status = {}
    context.latest_phase_timings = {}
    return context


@pytest.fixture
def mock_dspy_module():
    """Create a mock DSPy module."""
    module = MagicMock()
    # Make the module callable
    module.return_value = MagicMock(answer="42")
    return module


# =============================================================================
# Test: DSPyExecutor
# =============================================================================


class TestDSPyExecutor:
    """Tests for DSPyExecutor."""

    def test_initializes_with_required_params(self, mock_dspy_module, mock_supervisor_context):
        """Test that executor initializes correctly."""
        executor = DSPyExecutor(
            executor_id="dspy-1",
            module=mock_dspy_module,
            input_mapper=lambda x: {"question": x},
            output_mapper=lambda x, y: y.answer,
            context=mock_supervisor_context,
        )

        assert executor.id == "dspy-1"
        assert executor.module == mock_dspy_module
        assert executor.context == mock_supervisor_context

    @pytest.mark.asyncio
    async def test_handle_message_success(self, mock_dspy_module, mock_supervisor_context):
        """Test successful message handling."""
        # Setup
        executor = DSPyExecutor(
            executor_id="dspy-1",
            module=mock_dspy_module,
            input_mapper=lambda msg: {"question": msg["text"]},
            output_mapper=lambda msg, pred: {"original": msg["text"], "answer": pred.answer},
            context=mock_supervisor_context,
        )

        mock_ctx = MagicMock()
        mock_ctx.send_message = AsyncMock()

        input_msg = {"text": "What is the meaning of life?"}

        # Execute
        await executor.handle_message(input_msg, mock_ctx)

        # Verify module call
        mock_dspy_module.assert_called_once_with(question="What is the meaning of life?")

        # Verify context update
        assert mock_supervisor_context.latest_phase_status["dspy-1"] == "success"
        assert "dspy-1" in mock_supervisor_context.latest_phase_timings

        # Verify output message
        mock_ctx.send_message.assert_called_once()
        call_args = mock_ctx.send_message.call_args[0][0]
        assert call_args == {"original": "What is the meaning of life?", "answer": "42"}

    @pytest.mark.asyncio
    async def test_handle_message_failure(self, mock_dspy_module, mock_supervisor_context):
        """Test message handling failure."""
        # Setup module to raise exception
        mock_dspy_module.side_effect = ValueError("DSPy error")

        executor = DSPyExecutor(
            executor_id="dspy-1",
            module=mock_dspy_module,
            input_mapper=lambda msg: {"question": msg},
            output_mapper=lambda msg, pred: pred,
            context=mock_supervisor_context,
        )

        mock_ctx = MagicMock()

        # Execute and expect error
        with pytest.raises(ValueError, match="DSPy error"):
            await executor.handle_message("test", mock_ctx)

        # Verify status update
        assert mock_supervisor_context.latest_phase_status["dspy-1"] == "failed"
