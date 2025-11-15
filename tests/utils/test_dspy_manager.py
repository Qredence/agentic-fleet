"""
Tests for centralized DSPy LM management.
"""

from unittest.mock import MagicMock, patch

from agentic_fleet.utils.dspy_manager import (
    configure_dspy_settings,
    get_current_lm,
    get_dspy_lm,
    get_reflection_lm,
    reset_dspy_manager,
)


class TestDSPyManager:
    """Test centralized DSPy LM management."""

    def test_get_dspy_lm_creates_instance(self):
        """Test that get_dspy_lm creates an LM instance."""
        reset_dspy_manager()

        with patch("agentic_fleet.utils.dspy_manager.dspy") as mock_dspy:
            mock_lm = MagicMock()
            mock_dspy.LM.return_value = mock_lm

            lm = get_dspy_lm("gpt-4")

            assert lm == mock_lm
            mock_dspy.LM.assert_called_once_with("openai/gpt-4")

    def test_get_dspy_lm_reuses_instance(self):
        """Test that get_dspy_lm reuses the same instance for the same model."""
        reset_dspy_manager()

        with patch("agentic_fleet.utils.dspy_manager.dspy") as mock_dspy:
            mock_lm = MagicMock()
            mock_dspy.LM.return_value = mock_lm

            lm1 = get_dspy_lm("gpt-4")
            lm2 = get_dspy_lm("gpt-4")

            assert lm1 is lm2
            # Should only be called once
            assert mock_dspy.LM.call_count == 1

    def test_get_dspy_lm_creates_new_for_different_model(self):
        """Test that get_dspy_lm creates new instance for different model."""
        reset_dspy_manager()

        with patch("agentic_fleet.utils.dspy_manager.dspy") as mock_dspy:
            mock_lm1 = MagicMock()
            mock_lm2 = MagicMock()
            mock_dspy.LM.side_effect = [mock_lm1, mock_lm2]

            lm1 = get_dspy_lm("gpt-4")
            lm2 = get_dspy_lm("gpt-5-mini")

            assert lm1 is not lm2
            assert mock_dspy.LM.call_count == 2

    def test_configure_dspy_settings(self):
        """Test that configure_dspy_settings configures DSPy."""
        reset_dspy_manager()

        with patch("agentic_fleet.utils.dspy_manager.dspy") as mock_dspy:
            mock_lm = MagicMock()
            mock_dspy.LM.return_value = mock_lm
            mock_dspy.settings.configure = MagicMock()

            result = configure_dspy_settings("gpt-4", enable_cache=True)

            assert result is True
            mock_dspy.settings.configure.assert_called_once_with(lm=mock_lm)

    def test_configure_dspy_settings_handles_async_conflict(self):
        """Test that configure_dspy_settings handles async context conflicts."""
        reset_dspy_manager()

        with patch("agentic_fleet.utils.dspy_manager.dspy") as mock_dspy:
            mock_lm = MagicMock()
            mock_dspy.LM.return_value = mock_lm
            mock_dspy.settings.configure.side_effect = RuntimeError(
                "can only be called from the same async task"
            )

            result = configure_dspy_settings("gpt-4")

            # Should return False (already configured) without raising
            assert result is False

    def test_get_reflection_lm(self):
        """Test that get_reflection_lm returns LM instance."""
        reset_dspy_manager()

        with patch("agentic_fleet.utils.dspy_manager.dspy") as mock_dspy:
            mock_lm = MagicMock()
            mock_dspy.LM.return_value = mock_lm

            lm = get_reflection_lm("gpt-4")

            assert lm == mock_lm

    def test_get_reflection_lm_returns_none_for_none(self):
        """Test that get_reflection_lm returns None when model is None."""
        reset_dspy_manager()

        lm = get_reflection_lm(None)

        assert lm is None

    def test_reset_dspy_manager(self):
        """Test that reset_dspy_manager clears global state."""
        reset_dspy_manager()

        with patch("agentic_fleet.utils.dspy_manager.dspy") as mock_dspy:
            mock_lm = MagicMock()
            mock_dspy.LM.return_value = mock_lm

            get_dspy_lm("gpt-4")
            assert get_current_lm() is not None

            reset_dspy_manager()
            assert get_current_lm() is None
