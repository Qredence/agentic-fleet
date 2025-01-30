"""Unit tests for CLI module."""
import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from agentic_fleet.cli import cli, get_app_path, get_config_path


def test_get_app_path():
    """Test get_app_path returns correct path."""
    app_path = get_app_path()
    assert os.path.exists(app_path)
    assert app_path.endswith("app.py")


def test_get_config_path_default():
    """Test get_config_path with default OAuth setting."""
    config_path = get_config_path()
    assert config_path.endswith("config.oauth.toml")


def test_get_config_path_no_oauth():
    """Test get_config_path with OAuth disabled."""
    config_path = get_config_path(no_oauth=True)
    assert config_path.endswith("config.no-oauth.toml")


def test_cli_start_default():
    """Test CLI start command with default settings."""
    runner = CliRunner()
    with patch('subprocess.run') as mock_run:
        result = runner.invoke(cli, ["start"])
        assert result.exit_code == 0
        assert "Starting AgenticFleet with OAuth..." in result.output
        mock_run.assert_called_once()


def test_cli_start_no_oauth():
    """Test CLI start command with OAuth disabled."""
    runner = CliRunner()
    with patch('subprocess.run') as mock_run:
        result = runner.invoke(cli, ["start", "no-oauth"])
        assert result.exit_code == 0
        assert "Starting AgenticFleet without OAuth..." in result.output
        mock_run.assert_called_once()


def test_cli_start_invalid_mode():
    """Test CLI start command with invalid mode."""
    runner = CliRunner()
    result = runner.invoke(cli, ["start", "invalid"])
    assert result.exit_code == 2
    assert "Invalid value for 'MODE'" in result.output
