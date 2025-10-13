"""
Tests for workflow checkpointing functionality.

This module contains pytest tests that validate:
1. Checkpoint storage configuration
2. Checkpoint creation and restoration
3. Workflow resumption after failures
4. Checkpoint listing and management
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agenticfleet.config.settings import Settings
from agenticfleet.workflows.multi_agent import MultiAgentWorkflow


@pytest.fixture
def temp_checkpoint_dir():
    """Create a temporary directory for checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_settings(temp_checkpoint_dir):
    """Create a mock settings instance with checkpointing enabled."""
    settings = Mock(spec=Settings)
    settings.workflow_config = {
        "workflow": {
            "max_rounds": 5,
            "max_stalls": 2,
            "checkpointing": {
                "enabled": True,
                "storage_type": "file",
                "storage_path": temp_checkpoint_dir,
            },
        }
    }
    return settings


def test_checkpoint_storage_creation_file():
    """Test that file-based checkpoint storage is created correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("agenticfleet.config.settings.Settings.__init__", return_value=None):
            settings = Settings()
            settings.workflow_config = {
                "workflow": {
                    "checkpointing": {
                        "enabled": True,
                        "storage_type": "file",
                        "storage_path": tmpdir,
                    }
                }
            }

            storage = settings.create_checkpoint_storage()
            assert storage is not None
            assert hasattr(storage, "storage_path")
            assert Path(tmpdir).exists()


def test_checkpoint_storage_creation_memory():
    """Test that memory-based checkpoint storage is created correctly."""
    with patch("agenticfleet.config.settings.Settings.__init__", return_value=None):
        settings = Settings()
        settings.workflow_config = {
            "workflow": {
                "checkpointing": {
                    "enabled": True,
                    "storage_type": "memory",
                }
            }
        }

        storage = settings.create_checkpoint_storage()
        assert storage is not None


def test_checkpoint_storage_disabled():
    """Test that checkpoint storage returns None when disabled."""
    with patch("agenticfleet.config.settings.Settings.__init__", return_value=None):
        settings = Settings()
        settings.workflow_config = {
            "workflow": {
                "checkpointing": {
                    "enabled": False,
                }
            }
        }

        storage = settings.create_checkpoint_storage()
        assert storage is None


@pytest.mark.asyncio
async def test_workflow_checkpoint_creation(temp_checkpoint_dir):
    """Test that workflow creates checkpoints correctly."""
    from agent_framework import FileCheckpointStorage

    checkpoint_storage = FileCheckpointStorage(temp_checkpoint_dir)

    # Mock the agents to avoid actual API calls
    with (
        patch("agenticfleet.workflows.multi_agent.create_orchestrator_agent"),
        patch("agenticfleet.workflows.multi_agent.create_researcher_agent"),
        patch("agenticfleet.workflows.multi_agent.create_coder_agent"),
        patch("agenticfleet.workflows.multi_agent.create_analyst_agent"),
        patch("agenticfleet.config.settings.settings") as mock_settings,
    ):

        mock_settings.workflow_config = {
            "workflow": {
                "max_rounds": 5,
                "max_stalls": 2,
            }
        }

        workflow = MultiAgentWorkflow(checkpoint_storage=checkpoint_storage)
        workflow.set_workflow_id("test_workflow")

        # Set up some state
        workflow.current_round = 2
        workflow.stall_count = 0
        workflow.last_response = "Test response"
        workflow.context = {"test": "data"}

        # Create checkpoint
        checkpoint_id = await workflow.create_checkpoint({"status": "test"})

        assert checkpoint_id is not None
        assert workflow.current_checkpoint_id == checkpoint_id

        # Verify checkpoint file exists
        checkpoint_path = Path(temp_checkpoint_dir) / f"{checkpoint_id}.json"
        assert checkpoint_path.exists()

        # Verify checkpoint content
        with open(checkpoint_path) as f:
            data = json.load(f)

        assert data["checkpoint_id"] == checkpoint_id
        assert data["workflow_id"] == "test_workflow"
        assert data["current_round"] == 2
        assert data["stall_count"] == 0
        assert data["last_response"] == "Test response"
        assert data["context"] == {"test": "data"}
        assert data["metadata"]["status"] == "test"


@pytest.mark.asyncio
async def test_workflow_checkpoint_restoration(temp_checkpoint_dir):
    """Test that workflow can restore from checkpoints."""
    from agent_framework import FileCheckpointStorage

    checkpoint_storage = FileCheckpointStorage(temp_checkpoint_dir)

    with (
        patch("agenticfleet.workflows.multi_agent.create_orchestrator_agent"),
        patch("agenticfleet.workflows.multi_agent.create_researcher_agent"),
        patch("agenticfleet.workflows.multi_agent.create_coder_agent"),
        patch("agenticfleet.workflows.multi_agent.create_analyst_agent"),
        patch("agenticfleet.config.settings.settings") as mock_settings,
    ):

        mock_settings.workflow_config = {
            "workflow": {
                "max_rounds": 5,
                "max_stalls": 2,
            }
        }

        # Create first workflow and checkpoint
        workflow1 = MultiAgentWorkflow(checkpoint_storage=checkpoint_storage)
        workflow1.set_workflow_id("test_workflow")
        workflow1.current_round = 3
        workflow1.stall_count = 1
        workflow1.last_response = "Previous response"
        workflow1.context = {"important": "state"}

        checkpoint_id = await workflow1.create_checkpoint({"phase": "middle"})

        # Create new workflow and restore
        workflow2 = MultiAgentWorkflow(checkpoint_storage=checkpoint_storage)
        restored = await workflow2.restore_from_checkpoint(checkpoint_id)

        assert restored is True
        assert workflow2.workflow_id == "test_workflow"
        assert workflow2.current_round == 3
        assert workflow2.stall_count == 1
        assert workflow2.last_response == "Previous response"
        assert workflow2.context == {"important": "state"}
        assert workflow2.current_checkpoint_id == checkpoint_id


@pytest.mark.asyncio
async def test_workflow_checkpoint_restoration_missing(temp_checkpoint_dir):
    """Test that workflow handles missing checkpoint gracefully."""
    from agent_framework import FileCheckpointStorage

    checkpoint_storage = FileCheckpointStorage(temp_checkpoint_dir)

    with (
        patch("agenticfleet.workflows.multi_agent.create_orchestrator_agent"),
        patch("agenticfleet.workflows.multi_agent.create_researcher_agent"),
        patch("agenticfleet.workflows.multi_agent.create_coder_agent"),
        patch("agenticfleet.workflows.multi_agent.create_analyst_agent"),
        patch("agenticfleet.config.settings.settings") as mock_settings,
    ):

        mock_settings.workflow_config = {
            "workflow": {
                "max_rounds": 5,
                "max_stalls": 2,
            }
        }

        workflow = MultiAgentWorkflow(checkpoint_storage=checkpoint_storage)
        restored = await workflow.restore_from_checkpoint("nonexistent_checkpoint_id")

        assert restored is False


@pytest.mark.asyncio
async def test_workflow_list_checkpoints(temp_checkpoint_dir):
    """Test that workflow can list checkpoints."""
    from agent_framework import FileCheckpointStorage

    checkpoint_storage = FileCheckpointStorage(temp_checkpoint_dir)

    with (
        patch("agenticfleet.workflows.multi_agent.create_orchestrator_agent"),
        patch("agenticfleet.workflows.multi_agent.create_researcher_agent"),
        patch("agenticfleet.workflows.multi_agent.create_coder_agent"),
        patch("agenticfleet.workflows.multi_agent.create_analyst_agent"),
        patch("agenticfleet.config.settings.settings") as mock_settings,
    ):

        mock_settings.workflow_config = {
            "workflow": {
                "max_rounds": 5,
                "max_stalls": 2,
            }
        }

        workflow = MultiAgentWorkflow(checkpoint_storage=checkpoint_storage)
        workflow.set_workflow_id("workflow_1")

        # Create multiple checkpoints
        cp1 = await workflow.create_checkpoint({"status": "checkpoint_1"})
        workflow.current_round += 1
        cp2 = await workflow.create_checkpoint({"status": "checkpoint_2"})

        # List all checkpoints
        checkpoints = await workflow.list_checkpoints()
        assert len(checkpoints) >= 2

        # Verify checkpoint data
        checkpoint_ids = [cp["checkpoint_id"] for cp in checkpoints]
        assert cp1 in checkpoint_ids
        assert cp2 in checkpoint_ids

        # List checkpoints for specific workflow
        workflow_checkpoints = await workflow.list_checkpoints("workflow_1")
        assert len(workflow_checkpoints) >= 2


@pytest.mark.asyncio
async def test_workflow_no_checkpoint_storage():
    """Test that workflow works without checkpoint storage."""
    with (
        patch("agenticfleet.workflows.multi_agent.create_orchestrator_agent"),
        patch("agenticfleet.workflows.multi_agent.create_researcher_agent"),
        patch("agenticfleet.workflows.multi_agent.create_coder_agent"),
        patch("agenticfleet.workflows.multi_agent.create_analyst_agent"),
        patch("agenticfleet.config.settings.settings") as mock_settings,
    ):

        mock_settings.workflow_config = {
            "workflow": {
                "max_rounds": 5,
                "max_stalls": 2,
            }
        }

        workflow = MultiAgentWorkflow(checkpoint_storage=None)

        # Try to create checkpoint - should return None
        checkpoint_id = await workflow.create_checkpoint()
        assert checkpoint_id is None

        # Try to restore - should return False
        restored = await workflow.restore_from_checkpoint("any_id")
        assert restored is False

        # Try to list - should return empty list
        checkpoints = await workflow.list_checkpoints()
        assert checkpoints == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
