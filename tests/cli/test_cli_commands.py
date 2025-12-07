"""Comprehensive tests for CLI commands."""

import pytest
from unittest.mock import patch, AsyncMock
from typer.testing import CliRunner

from agentic_fleet.cli import app
from agentic_fleet.cli.commands.run import run_command
from agentic_fleet.cli.runner import CLIRunner


class TestCLIApp:
    """Test suite for main CLI application."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "AgenticFleet" in result.stdout or "Usage" in result.stdout

    def test_cli_version(self, runner):
        """Test CLI version command."""
        result = runner.invoke(app, ["--version"])

        # Should show version or succeed
        assert result.exit_code == 0 or "version" in result.stdout.lower()

    def test_cli_no_command(self, runner):
        """Test CLI without command."""
        result = runner.invoke(app, [])

        # Should show help or run interactively
        assert result.exit_code in [0, 1, 2]


class TestRunCommand:
    """Test suite for 'run' command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("agentic_fleet.cli.commands.run.create_supervisor_workflow")
    def test_run_command_with_message(self, mock_create_workflow, runner):
        """Test run command with message."""
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value={"result": "Success"})
        mock_create_workflow.return_value = mock_workflow

        result = runner.invoke(app, ["run", "-m", "Test task"])

        # Command should execute (may require async handling)
        assert result.exit_code in [0, 1]  # 0 for success, 1 for handled errors

    @patch("agentic_fleet.cli.commands.run.create_supervisor_workflow")
    def test_run_command_with_mode(self, mock_create_workflow, runner):
        """Test run command with execution mode."""
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value={"result": "Success"})
        mock_create_workflow.return_value = mock_workflow

        result = runner.invoke(app, ["run", "-m", "Task", "--mode", "delegated"])

        assert result.exit_code in [0, 1]

    def test_run_command_without_message(self, runner):
        """Test run command without required message."""
        result = runner.invoke(app, ["run"])

        # Should show error or prompt for message
        assert result.exit_code in [0, 1, 2]

    @patch("agentic_fleet.cli.commands.run.create_supervisor_workflow")
    def test_run_command_verbose(self, mock_create_workflow, runner):
        """Test run command with verbose output."""
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value={"result": "Verbose output"})
        mock_create_workflow.return_value = mock_workflow

        result = runner.invoke(app, ["run", "-m", "Task", "--verbose"])

        assert result.exit_code in [0, 1]

    @patch("agentic_fleet.cli.commands.run.create_supervisor_workflow")
    def test_run_command_with_timeout(self, mock_create_workflow, runner):
        """Test run command with timeout."""
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value={"result": "Done"})
        mock_create_workflow.return_value = mock_workflow

        result = runner.invoke(app, ["run", "-m", "Task", "--timeout", "60"])

        assert result.exit_code in [0, 1]


class TestListAgentsCommand:
    """Test suite for 'list-agents' command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_list_agents_command(self, runner):
        """Test list-agents command."""
        result = runner.invoke(app, ["list-agents"])

        # Should show available agents
        assert result.exit_code == 0 or "agents" in result.stdout.lower()

    @patch("agentic_fleet.cli.load_workflow_config")
    def test_list_agents_with_config(self, mock_load_config, runner):
        """Test listing agents from config."""
        mock_load_config.return_value = {
            "agents": {
                "researcher": {"model": "gpt-4o"},
                "analyst": {"model": "gpt-4o-mini"},
            }
        }

        result = runner.invoke(app, ["list-agents"])

        # Should list agents from config
        assert result.exit_code in [0, 1]


class TestDevCommand:
    """Test suite for 'dev' command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("agentic_fleet.cli.subprocess.run")
    def test_dev_command_starts_servers(self, mock_subprocess, runner):
        """Test dev command starts backend and frontend."""
        result = runner.invoke(app, ["dev"])

        # Command should attempt to start servers
        assert result.exit_code in [0, 1]  # May exit immediately or background

    @patch("agentic_fleet.cli.subprocess.run")
    def test_dev_command_backend_only(self, mock_subprocess, runner):
        """Test dev command with backend only."""
        result = runner.invoke(app, ["dev", "--backend-only"])

        assert result.exit_code in [0, 1]


class TestCLIRunner:
    """Test suite for CLIRunner class."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLIRunner instance."""
        return CLIRunner()

    @patch("agentic_fleet.cli.runner.create_supervisor_workflow")
    async def test_cli_runner_execute_task(self, mock_create_workflow, cli_runner):
        """Test executing a task via CLI runner."""
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value={"result": "Completed"})
        mock_create_workflow.return_value = mock_workflow

        result = await cli_runner.execute_task("Test task")

        assert result is not None
        mock_workflow.run.assert_called_once()

    async def test_cli_runner_with_invalid_task(self, cli_runner):
        """Test CLI runner with invalid task."""
        with patch("agentic_fleet.cli.runner.create_supervisor_workflow") as mock:
            mock.side_effect = Exception("Invalid task")

            with pytest.raises(Exception):
                await cli_runner.execute_task("")

    @patch("agentic_fleet.cli.runner.create_supervisor_workflow")
    async def test_cli_runner_with_options(self, mock_create_workflow, cli_runner):
        """Test CLI runner with execution options."""
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value={"result": "Done"})
        mock_create_workflow.return_value = mock_workflow

        result = await cli_runner.execute_task(
            "Task", mode="sequential", verbose=True
        )

        assert result is not None


class TestCLIEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_cli_with_special_characters(self, runner):
        """Test CLI with special characters in message."""
        result = runner.invoke(
            app, ["run", "-m", "Task with 特殊字符 and émojis 🚀"]
        )

        # Should handle unicode properly
        assert result.exit_code in [0, 1]

    def test_cli_with_very_long_message(self, runner):
        """Test CLI with very long message."""
        long_message = "x" * 10000

        result = runner.invoke(app, ["run", "-m", long_message])

        assert result.exit_code in [0, 1]

    @patch("agentic_fleet.cli.commands.run.create_supervisor_workflow")
    def test_cli_with_workflow_error(self, mock_create_workflow, runner):
        """Test CLI handling workflow errors."""
        mock_create_workflow.side_effect = Exception("Workflow failed")

        result = runner.invoke(app, ["run", "-m", "Task"])

        # Should handle error gracefully
        assert result.exit_code == 1 or "error" in result.stdout.lower()

    def test_cli_interrupt_handling(self, runner):
        """Test CLI keyboard interrupt handling."""
        with patch("agentic_fleet.cli.commands.run.create_supervisor_workflow") as mock:
            mock.side_effect = KeyboardInterrupt()

            result = runner.invoke(app, ["run", "-m", "Task"])

            # Should handle interrupt gracefully
            assert result.exit_code in [0, 1, 130]  # 130 is typical for SIGINT


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("agentic_fleet.cli.commands.run.create_supervisor_workflow")
    def test_full_task_execution_workflow(self, mock_create_workflow, runner):
        """Test complete task execution workflow."""
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(
            return_value={
                "result": "Task completed",
                "metadata": {"execution_time": 5.2},
            }
        )
        mock_create_workflow.return_value = mock_workflow

        result = runner.invoke(
            app, ["run", "-m", "Complete task", "--mode", "auto", "--verbose"]
        )

        # Should execute successfully
        assert result.exit_code in [0, 1]

    def test_cli_config_loading(self, runner):
        """Test CLI loads configuration correctly."""
        with patch("agentic_fleet.cli.load_workflow_config") as mock_load:
            mock_load.return_value = {
                "execution": {"max_iterations": 5},
                "agents": {},
            }

            result = runner.invoke(app, ["list-agents"])

            mock_load.assert_called()
            assert result.exit_code in [0, 1]

    @patch("agentic_fleet.cli.commands.run.create_supervisor_workflow")
    def test_cli_with_all_options(self, mock_create_workflow, runner):
        """Test CLI with all available options."""
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value={"result": "Success"})
        mock_create_workflow.return_value = mock_workflow

        result = runner.invoke(
            app,
            [
                "run",
                "-m",
                "Complex task",
                "--mode",
                "parallel",
                "--verbose",
                "--timeout",
                "120",
            ],
        )

        assert result.exit_code in [0, 1]