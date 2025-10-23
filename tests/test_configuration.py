"""Tests for configuration helpers and default fleet factory.

These tests focus on ensuring checkpoint storage is created according to the
settings and that the default Magentic fleet wiring honours configuration.
"""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from agenticfleet.config.settings import Settings
from agenticfleet.fleet import MagenticFleet, create_default_fleet


def test_checkpoint_storage_creation_file() -> None:
    """File-based checkpoint storage should create the target directory."""
    with (
        tempfile.TemporaryDirectory() as tmpdir,
        patch("agenticfleet.config.settings.Settings.__init__", return_value=None),
    ):
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


def test_checkpoint_storage_creation_memory() -> None:
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


def test_checkpoint_storage_disabled() -> None:
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


def test_create_default_fleet_returns_magentic_fleet() -> None:
    """Factory should create a MagenticFleet with configured checkpoint storage."""
    checkpoint_storage = MagicMock()

    hitl_config = {
        "enabled": True,
        "require_approval_for": ["code_execution"],
        "trusted_operations": ["web_search"],
    }

    with (
        patch("agenticfleet.fleet.magentic_fleet.create_researcher_agent"),
        patch("agenticfleet.fleet.magentic_fleet.create_coder_agent"),
        patch("agenticfleet.fleet.magentic_fleet.create_analyst_agent"),
        patch("agenticfleet.fleet.magentic_fleet.set_approval_handler") as mock_set_handler,
        patch("agenticfleet.fleet.magentic_fleet.settings") as mock_settings,
    ):
        mock_settings.create_checkpoint_storage.return_value = checkpoint_storage
        mock_settings.workflow_config = {
            "workflow": {"human_in_the_loop": hitl_config},
        }

        fleet = create_default_fleet()

    assert isinstance(fleet, MagenticFleet)
    assert fleet.checkpoint_storage is checkpoint_storage
    mock_set_handler.assert_called_once()
    handler_arg = mock_set_handler.call_args.args[0]
    assert handler_arg is not None
    assert mock_set_handler.call_args.kwargs == {
        "require_operations": hitl_config["require_approval_for"],
        "trusted_operations": hitl_config["trusted_operations"],
    }


def test_redis_helpers_without_dependency(monkeypatch: Any) -> None:
    """Redis helpers should degrade gracefully when redis extras are unavailable."""
    with (
        patch("agenticfleet.config.settings.Settings.__init__", return_value=None),
        patch("agenticfleet.config.settings._REDIS_AVAILABLE", False),
    ):
        settings = Settings()
        settings.workflow_config = {}
        settings.redis_url = "redis://example.com:6379/0"

        assert settings.redis_chat_message_store_factory() is None
        assert settings.create_redis_provider(agent_id="analyst") is None
        assert settings.create_context_providers(agent_id="analyst") == []
