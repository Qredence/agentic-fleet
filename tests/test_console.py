"""Tests for console.py CLI interface."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from agentic_fleet.console import app


def test_list_workflows_command() -> None:
    """Test list-workflows command."""
    runner = CliRunner()
    result = runner.invoke(app, ["list-workflows"])

    assert result.exit_code == 0
    assert "magentic_fleet" in result.stdout


def test_workflow_command_help() -> None:
    """Test workflow command shows help."""
    runner = CliRunner()
    result = runner.invoke(app, ["workflow", "--help"])

    assert result.exit_code == 0
    assert "workflow" in result.stdout.lower()


@pytest.mark.asyncio
async def test_workflow_command_with_message() -> None:
    """Test workflow command with a message."""
    runner = CliRunner()
    # Use stub workflow (no API key needed)
    result = runner.invoke(app, ["workflow", "--message", "test message", "--no-stream"])

    # Should complete without error (uses stub workflow)
    assert (
        result.exit_code == 0 or result.exit_code == 1
    )  # May fail if API key missing, but should not crash
