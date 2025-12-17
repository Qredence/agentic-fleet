"""Tests for lifespan DSPy artifact registry integration."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.api.lifespan import lifespan
from agentic_fleet.dspy_modules.compiled_registry import ArtifactRegistry


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app."""
    app = MagicMock()
    app.state = MagicMock()
    return app


class TestLifespanArtifactRegistry:
    """Tests for artifact registry integration in lifespan."""

    @pytest.mark.asyncio
    @patch("agentic_fleet.api.lifespan.create_supervisor_workflow")
    @patch("agentic_fleet.api.lifespan.load_required_compiled_modules")
    @patch("agentic_fleet.api.lifespan.load_config")
    @patch("agentic_fleet.api.lifespan.get_settings")
    async def test_lifespan_loads_artifacts_require_false(
        self,
        mock_get_settings,
        mock_load_config,
        mock_load_modules,
        mock_create_workflow,
        mock_app,
    ):
        """Test lifespan loads artifacts successfully with require_compiled=False."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.max_concurrent_workflows = 10
        mock_settings.conversations_path = ".var/data/conversations.json"
        mock_get_settings.return_value = mock_settings

        # Mock config
        mock_config = {
            "dspy": {
                "require_compiled": False,
                "compiled_routing_path": ".var/cache/dspy/compiled_routing.json",
            }
        }
        mock_load_config.return_value = mock_config

        # Mock workflow creation
        mock_workflow = MagicMock()
        mock_create_workflow.return_value = mock_workflow

        # Mock artifact registry
        mock_registry = ArtifactRegistry(
            routing=MagicMock(),
            tool_planning=MagicMock(),
            quality=MagicMock(),
        )
        mock_load_modules.return_value = mock_registry

        # Run lifespan
        async with lifespan(mock_app):
            # Verify workflow was created
            assert mock_app.state.workflow is mock_workflow

            # Verify artifacts were loaded
            assert hasattr(mock_app.state, "dspy_artifacts")
            assert mock_app.state.dspy_artifacts is mock_registry

            # Verify decision modules were initialized
            assert hasattr(mock_app.state, "dspy_quality_module")
            assert hasattr(mock_app.state, "dspy_routing_module")
            assert hasattr(mock_app.state, "dspy_tool_planning_module")

        # Verify cleanup
        assert mock_app.state.dspy_artifacts is None

    @pytest.mark.asyncio
    @patch("agentic_fleet.api.lifespan.create_supervisor_workflow")
    @patch("agentic_fleet.api.lifespan.load_required_compiled_modules")
    @patch("agentic_fleet.api.lifespan.load_config")
    @patch("agentic_fleet.api.lifespan.get_settings")
    async def test_lifespan_fails_fast_on_missing_required_artifacts(
        self,
        mock_get_settings,
        mock_load_config,
        mock_load_modules,
        mock_create_workflow,
        mock_app,
    ):
        """Test lifespan fails fast when required artifacts are missing."""
        # Mock settings
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        # Mock config with require_compiled=True
        mock_config = {
            "dspy": {
                "require_compiled": True,
            }
        }
        mock_load_config.return_value = mock_config

        # Mock workflow creation
        mock_workflow = MagicMock()
        mock_create_workflow.return_value = mock_workflow

        # Mock artifact loading to raise RuntimeError
        mock_load_modules.side_effect = RuntimeError(
            "Required compiled DSPy artifacts not found: ['routing', 'quality']"
        )

        # Lifespan should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            async with lifespan(mock_app):
                pass

        assert "Required compiled DSPy artifacts not found" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("agentic_fleet.api.lifespan.create_supervisor_workflow")
    @patch("agentic_fleet.api.lifespan.load_required_compiled_modules")
    @patch("agentic_fleet.api.lifespan.load_config")
    @patch("agentic_fleet.api.lifespan.get_settings")
    async def test_lifespan_continues_on_error_when_require_false(
        self,
        mock_get_settings,
        mock_load_config,
        mock_load_modules,
        mock_create_workflow,
        mock_app,
    ):
        """Test lifespan continues with warning when require_compiled=False and error occurs."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.max_concurrent_workflows = 10
        mock_settings.conversations_path = ".var/data/conversations.json"
        mock_get_settings.return_value = mock_settings

        # Mock config with require_compiled=False
        mock_config = {
            "dspy": {
                "require_compiled": False,
            }
        }
        mock_load_config.return_value = mock_config

        # Mock workflow creation
        mock_workflow = MagicMock()
        mock_create_workflow.return_value = mock_workflow

        # Mock artifact loading to raise generic exception (not RuntimeError)
        mock_load_modules.side_effect = ValueError("Unexpected error")

        # Lifespan should not raise when require_compiled=False
        async with lifespan(mock_app):
            # Verify workflow was still created
            assert mock_app.state.workflow is mock_workflow

            # Artifact registry should not be set due to error
            # (depending on implementation, may be None)
            pass
