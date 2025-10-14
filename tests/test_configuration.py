"""
Tests for configuration helpers and default fleet factory.

These tests focus on ensuring checkpoint storage is created according to the
settings and that the default Magentic fleet wiring honours configuration.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from agenticfleet.config.settings import Settings
from agenticfleet.fleet import MagenticFleet, create_default_fleet


def test_checkpoint_storage_creation_file():
    """File-based checkpoint storage should create the target directory."""
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
    """Memory-based checkpoint storage should be initialised when enabled."""
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
    """Checkpoint storage should be skipped when explicitly disabled."""
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


def test_create_default_fleet_returns_magentic_fleet():
    """Factory should create a MagenticFleet with configured checkpoint storage."""
    checkpoint_storage = MagicMock()

    with (
        patch("agenticfleet.fleet.magentic_fleet.create_researcher_agent"),
        patch("agenticfleet.fleet.magentic_fleet.create_coder_agent"),
        patch("agenticfleet.fleet.magentic_fleet.create_analyst_agent"),
        patch("agenticfleet.fleet.magentic_fleet.settings") as mock_settings,
    ):
        mock_settings.create_checkpoint_storage.return_value = checkpoint_storage
        mock_settings.workflow_config = {
            "workflow": {
                "human_in_the_loop": {"enabled": False},
            }
        }

        fleet = create_default_fleet()

    assert isinstance(fleet, MagenticFleet)
    assert fleet.checkpoint_storage is checkpoint_storage
