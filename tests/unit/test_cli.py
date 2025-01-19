"""Unit tests for CLI module."""
import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from agentic_fleet.cli import cli, setup_environment


def test_setup_environment_with_oauth():
    """Test setup_environment with OAuth enabled."""
    with patch.dict(os.environ, {}, clear=True):
        setup_environment(no_oauth=False)
        assert "OAUTH_CLIENT_ID" not in os.environ
        assert "OAUTH_CLIENT_SECRET" not in os.environ


def test_setup_environment_without_oauth():
    """Test setup_environment with OAuth disabled."""
    with patch.dict(os.environ, {}, clear=True):
        setup_environment(no_oauth=True)
        assert os.environ["OAUTH_CLIENT_ID"] == ""
        assert os.environ["OAUTH_CLIENT_SECRET"] == ""
        assert os.environ["OAUTH_REDIRECT_URI"] == ""


def test_cli_start_help():
    """Test CLI start command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["start", "--help"])
    assert result.exit_code == 0
    assert "Start the AgenticFleet server" in result.output
    assert "--no-oauth" in result.output
    assert "--port" in result.output
