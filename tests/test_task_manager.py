"""Tests for the task manager module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from enum import Enum

# Define TaskStatus enum locally since it's not available in chainlit.types
class TaskStatus(str, Enum):
    """Status of a task."""
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

from agentic_fleet.ui.task_manager import extract_and_add_plan_tasks, update_task_status


@pytest.mark.asyncio
async def test_extract_plan_tasks(mock_user_session, mock_chainlit_elements):
    """Test extracting tasks from a plan and adding them to a task list."""
    plan_text = """1. First step
    2. Second step
    - Bullet point
    * Another item"""
    
    task_list = MagicMock()
    task_list.add_task = AsyncMock()
    
    # Create mock Text objects
    planning_mock = mock_chainlit_elements["Text"].return_value
    overview_mock = mock_chainlit_elements["Text"].return_value
    
    task_status = {
        "planning": planning_mock,
        "overview": overview_mock
    }
    
    with patch("chainlit.TaskList", return_value=task_list):
        await extract_and_add_plan_tasks(
            plan_text,
            task_list,
            task_status,
            "test_message",
            False
        )
    
    # Check that add_task was called for each extracted task
    assert task_list.add_task.call_count == 4
    
    # Check that send was called on both mock Text objects
    assert planning_mock.send.called
    assert overview_mock.send.called


@pytest.mark.asyncio
async def test_extract_plan_tasks_with_update(mock_user_session, mock_chainlit_elements):
    """Test extracting tasks with the update flag set to True."""
    plan_text = "Updated plan with a single task"
    
    task_list = MagicMock()
    task_list.add_task = AsyncMock()
    
    # Create mock Text objects
    planning_mock = mock_chainlit_elements["Text"].return_value
    overview_mock = mock_chainlit_elements["Text"].return_value
    
    task_status = {
        "planning": planning_mock,
        "overview": overview_mock
    }
    
    with patch("chainlit.TaskList", return_value=task_list):
        await extract_and_add_plan_tasks(
            plan_text,
            task_list,
            task_status,
            "test_message",
            True  # Set is_update to True
        )
    
    # For update mode, we should still add the task
    assert task_list.add_task.called
    
    # Check that send was called on both mock Text objects
    assert planning_mock.send.called
    assert overview_mock.send.called


@pytest.mark.asyncio
async def test_update_task_status(mock_user_session, mock_chainlit_elements):
    """Test updating task status."""
    # Create a mock task
    mock_task = MagicMock()
    mock_task.id = "task_123"
    mock_task.status = TaskStatus.READY
    
    # Set up mock tasks in user session
    mock_user_session["tasks"] = [mock_task]
    
    # Create mock TaskList
    task_list = MagicMock()
    task_list.update_task = AsyncMock()
    
    with patch("chainlit.TaskList", return_value=task_list):
        await update_task_status("task_123", TaskStatus.RUNNING, "Working on task")
    
    # Check that task status was updated
    assert mock_task.status == TaskStatus.RUNNING
    assert task_list.update_task.called
    
    # Call should include the task_id and the updated status
    task_list.update_task.assert_called_once_with(
        "task_123",
        status=TaskStatus.RUNNING,
        title="Working on task"
    )


@pytest.mark.asyncio
async def test_update_task_status_nonexistent_task(mock_user_session, mock_chainlit_elements):
    """Test updating a task that doesn't exist."""
    # Set up mock tasks in user session
    mock_user_session["tasks"] = []
    
    # Create mock TaskList
    task_list = MagicMock()
    task_list.update_task = AsyncMock()
    
    with patch("chainlit.TaskList", return_value=task_list):
        # Should not raise an exception
        await update_task_status("nonexistent_task", TaskStatus.RUNNING)
    
    # update_task should not be called
    assert not task_list.update_task.called 