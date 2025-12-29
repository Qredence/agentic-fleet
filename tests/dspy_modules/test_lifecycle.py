import threading
from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.dspy_modules.lifecycle.manager import (
    DSPyManager,
    configure_dspy_settings,
    reset_dspy_manager,
)


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset the manager before and after each test."""
    reset_dspy_manager()
    yield
    reset_dspy_manager()


def test_singleton_behavior():
    """Test that DSPyManager is a singleton."""
    manager1 = DSPyManager()
    manager2 = DSPyManager()
    assert manager1 is manager2


def test_initialization_state():
    """Test initial state of the manager."""
    manager = DSPyManager()
    assert manager._lm is None
    assert manager._model_name is None
    assert manager._configured is False
    assert manager._langfuse_initialized is False


@patch("dspy.LM")
def test_get_lm_creates_instance(mock_lm_cls):
    """Test that get_lm creates a new LM instance."""
    manager = DSPyManager()
    mock_instance = MagicMock()
    mock_lm_cls.return_value = mock_instance

    lm = manager.get_lm("gpt-4-test")

    assert lm is mock_instance
    assert manager._lm is mock_instance
    assert manager._model_name == "gpt-4-test"
    mock_lm_cls.assert_called_once()


@patch("dspy.LM")
def test_get_lm_reuses_instance(mock_lm_cls):
    """Test that get_lm reuses the existing instance if model matches."""
    manager = DSPyManager()
    mock_instance = MagicMock()
    mock_lm_cls.return_value = mock_instance

    lm1 = manager.get_lm("gpt-4-test")
    lm2 = manager.get_lm("gpt-4-test")

    assert lm1 is lm2
    mock_lm_cls.assert_called_once()


@patch("dspy.LM")
def test_get_lm_recreates_on_model_change(mock_lm_cls):
    """Test that get_lm creates a new instance if model changes."""
    manager = DSPyManager()

    # Return different instances for each call
    mock_lm_cls.side_effect = [MagicMock(name="lm1"), MagicMock(name="lm2")]

    lm1 = manager.get_lm("gpt-4-test")
    lm2 = manager.get_lm("gpt-3.5-test")

    assert lm1 is not lm2
    assert manager._model_name == "gpt-3.5-test"
    assert mock_lm_cls.call_count == 2


@patch("dspy.settings")
@patch("dspy.LM")
def test_configure_dspy_settings(mock_lm_cls, mock_settings):
    """Test configure_dspy_settings wrapper."""
    # Mock configure method on the settings object
    mock_settings.configure = MagicMock()

    result = configure_dspy_settings("gpt-4-test")

    assert result is True
    mock_settings.configure.assert_called_once()
    assert DSPyManager()._configured is True


@patch("dspy.settings")
@patch("dspy.LM")
def test_configure_idempotency(mock_lm_cls, mock_settings):
    """Test that configure is idempotent."""
    mock_settings.configure = MagicMock()

    configure_dspy_settings("gpt-4-test")
    mock_settings.configure.reset_mock()

    result = configure_dspy_settings("gpt-4-test")

    assert result is False
    mock_settings.configure.assert_not_called()


@patch("dspy.settings")
@patch("dspy.LM")
def test_configure_force_reconfigure(mock_lm_cls, mock_settings):
    """Test force_reconfigure option."""
    mock_settings.configure = MagicMock()

    configure_dspy_settings("gpt-4-test")
    mock_settings.configure.reset_mock()

    result = configure_dspy_settings("gpt-4-test", force_reconfigure=True)

    assert result is True
    mock_settings.configure.assert_called_once()


def test_thread_safety():
    """Test basic thread safety of singleton access."""
    managers = []

    def get_manager():
        managers.append(DSPyManager())

    threads = [threading.Thread(target=get_manager) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(managers) == 10
    assert all(m is managers[0] for m in managers)
