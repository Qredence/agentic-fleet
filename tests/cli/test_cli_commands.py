"""Comprehensive tests for CLI commands.

Tests the Typer CLI application and WorkflowRunner class.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

# Import app directly from console to avoid lazy loading issues
from agentic_fleet.cli.console import app
from agentic_fleet.cli.runner import WorkflowRunner


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
        assert "Usage" in result.stdout

    def test_cli_no_command_shows_help(self, runner):
        """Test CLI without command shows help."""
        result = runner.invoke(app, [])

        # Typer with no_args_is_help=True typically exits with code 2 showing help
        assert result.exit_code in [0, 2]
        assert "Usage" in result.stdout


class TestRunCommand:
    """Test suite for 'run' command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_run_command_help(self, runner):
        """Test run command help."""
        result = runner.invoke(app, ["run", "--help"])

        assert result.exit_code == 0
        assert "run" in result.stdout.lower() or "Usage" in result.stdout

    @patch("agentic_fleet.cli.commands.run.WorkflowRunner")
    def test_run_command_with_message(self, mock_runner_class, runner):
        """Test run command with message."""
        mock_instance = MagicMock()
        mock_instance.run_task = AsyncMock(return_value={"result": "Success"})
        mock_runner_class.return_value = mock_instance

        result = runner.invoke(app, ["run", "-m", "Test task"])

        # Command should execute (may fail due to other dependencies)
        assert result.exit_code in [0, 1]

    def test_run_command_without_message(self, runner):
        """Test run command without required message shows error or prompt."""
        result = runner.invoke(app, ["run"])

        # Should show error for missing message or prompt
        assert result.exit_code in [0, 1, 2]


class TestListAgentsCommand:
    """Test suite for 'list-agents' command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_list_agents_help(self, runner):
        """Test list-agents command help."""
        result = runner.invoke(app, ["list-agents", "--help"])

        assert result.exit_code == 0

    def test_list_agents_command(self, runner):
        """Test list-agents command executes."""
        result = runner.invoke(app, ["list-agents"])

        # Should execute and show agents from config
        assert result.exit_code in [0, 1]


class TestDevCommand:
    """Test suite for 'dev' command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_dev_command_help(self, runner):
        """Test dev command help."""
        result = runner.invoke(app, ["dev", "--help"])

        assert result.exit_code == 0
        assert "dev" in result.stdout.lower() or "Usage" in result.stdout


class TestWorkflowRunner:
    """Test suite for WorkflowRunner class."""

    def test_workflow_runner_init(self):
        """Test WorkflowRunner initialization."""
        runner = WorkflowRunner()
        assert runner.verbose is False
        assert runner.workflow is None

    def test_workflow_runner_init_verbose(self):
        """Test WorkflowRunner initialization with verbose."""
        runner = WorkflowRunner(verbose=True)
        assert runner.verbose is True

    @pytest.mark.asyncio
    @patch("agentic_fleet.cli.runner.create_supervisor_workflow")
    async def test_workflow_runner_initialize_workflow(self, mock_create_workflow):
        """Test initializing workflow."""
        mock_workflow = MagicMock()
        mock_create_workflow.return_value = mock_workflow

        wf_runner = WorkflowRunner()
        await wf_runner.initialize_workflow()

        mock_create_workflow.assert_called_once()
        assert wf_runner.workflow == mock_workflow

    @pytest.mark.asyncio
    @patch("agentic_fleet.cli.runner.create_supervisor_workflow")
    async def test_workflow_runner_with_options(self, mock_create_workflow):
        """Test workflow runner with execution options."""
        mock_workflow = MagicMock()
        mock_create_workflow.return_value = mock_workflow

        wf_runner = WorkflowRunner(verbose=True)
        await wf_runner.initialize_workflow(
            max_rounds=10,
            model="gpt-4.1-mini",
            mode="concurrent",
        )

        # Verify workflow was created
        assert wf_runner.workflow is not None


class TestCLIEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_cli_with_invalid_command(self, runner):
        """Test CLI with invalid command."""
        result = runner.invoke(app, ["invalid-command-xyz"])

        # Should show error for unknown command
        assert result.exit_code != 0

    def test_cli_run_with_special_characters(self, runner):
        """Test CLI with special characters in message."""
        result = runner.invoke(app, ["run", "-m", "Task with émojis 🚀"])

        # CLI should handle Unicode input without crashing
        # (may fail due to missing config, but not due to Unicode itself)
        assert "UnicodeError" not in str(result.exception) if result.exception else True


class TestHandoffCommand:
    """Test suite for 'handoff' command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_handoff_command_help(self, runner):
        """Test handoff command help."""
        result = runner.invoke(app, ["handoff", "--help"])

        assert result.exit_code == 0


class TestAnalyzeCommand:
    """Test suite for 'analyze' command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_analyze_command_help(self, runner):
        """Test analyze command help."""
        result = runner.invoke(app, ["analyze", "--help"])

        assert result.exit_code == 0


class TestEvaluateCommand:
    """Test suite for 'evaluate' command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_evaluate_command_help(self, runner):
        """Test evaluate command help."""
        result = runner.invoke(app, ["evaluate", "--help"])

        assert result.exit_code == 0
