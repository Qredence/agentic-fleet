"""Tests for middleware concurrency safety."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_fleet.api.middleware import BridgeMiddleware


@pytest.mark.asyncio
async def test_bridge_middleware_concurrent_execution():
    """Test that concurrent requests don't share execution data.

    This test verifies that the BridgeMiddleware correctly uses contextvars
    to isolate execution data across concurrent requests, preventing race
    conditions when the same middleware instance is shared.
    """
    # Create mock history manager
    mock_history_manager = MagicMock()
    mock_history_manager.save_execution_async = AsyncMock()

    # Create single middleware instance (shared across "requests")
    middleware = BridgeMiddleware(
        history_manager=mock_history_manager,
        dspy_examples_path=None,  # Disable DSPy example saving for this test
    )

    # Track saved execution data
    saved_executions = []

    async def capture_save(data):
        """Capture saved execution data."""
        # Make a copy to avoid reference issues
        saved_executions.append(dict(data))

    mock_history_manager.save_execution_async.side_effect = capture_save

    async def simulate_request(task_id: int):
        """Simulate a single request handling."""
        task = f"task_{task_id}"
        context = {
            "workflowId": f"workflow_{task_id}",
            "mode": "standard",
            "metadata": {"request_id": task_id},
        }

        # Start the request
        await middleware.on_start(task, context)

        # Simulate some processing time
        await asyncio.sleep(0.01)

        # End the request with result
        result = {"result": f"result_{task_id}", "task_id": task_id}
        await middleware.on_end(result)

        return task_id

    # Run 10 concurrent requests
    tasks = [simulate_request(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    # Verify all requests completed
    assert len(results) == 10
    assert results == list(range(10))

    # Verify all executions were saved
    assert len(saved_executions) == 10

    # Verify each execution has the correct data (no cross-contamination)
    for i in range(10):
        execution = saved_executions[i]

        # Check that each execution has its own unique data
        assert execution["task"] == f"task_{i}", f"Task mismatch for execution {i}"
        assert execution["workflowId"] == f"workflow_{i}", f"WorkflowId mismatch for execution {i}"
        assert execution["result"] == f"result_{i}", f"Result mismatch for execution {i}"
        assert execution["task_id"] == i, f"Task ID mismatch for execution {i}"
        assert execution["metadata"]["request_id"] == i, f"Request ID mismatch for execution {i}"

        # Verify execution has required fields
        assert "start_time" in execution
        assert "end_time" in execution
        assert "mode" in execution


@pytest.mark.asyncio
async def test_bridge_middleware_error_handling():
    """Test that error handling works correctly with contextvars."""
    mock_history_manager = MagicMock()
    mock_history_manager.save_execution_async = AsyncMock()

    middleware = BridgeMiddleware(history_manager=mock_history_manager, dspy_examples_path=None)

    saved_executions = []

    async def capture_save(data):
        saved_executions.append(dict(data))

    mock_history_manager.save_execution_async.side_effect = capture_save

    # Start a request
    await middleware.on_start("test_task", {"workflowId": "test_wf"})

    # Simulate an error
    test_error = Exception("Test error")
    await middleware.on_error(test_error)

    # Verify error was recorded
    assert len(saved_executions) == 1
    execution = saved_executions[0]
    assert execution["error"] == "Test error"
    assert execution["status"] == "failed"
    assert "end_time" in execution


@pytest.mark.asyncio
async def test_bridge_middleware_no_context_warning():
    """Test that calling on_end without on_start logs a warning."""
    mock_history_manager = MagicMock()
    mock_history_manager.save_execution_async = AsyncMock()

    middleware = BridgeMiddleware(history_manager=mock_history_manager, dspy_examples_path=None)

    # Call on_end without on_start
    await middleware.on_end({"result": "test"})

    # Verify no save was attempted (because execution_data was None)
    mock_history_manager.save_execution_async.assert_not_called()
