"""Interactive CLI for running AgenticFleet workflows."""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.status import Status
    from rich.table import Table
    from rich.text import Text
except ImportError as e:
    raise ImportError("rich package is required for CLI. Install with: uv add rich") from e

from agentic_fleet.utils.factory import WorkflowFactory

logger = logging.getLogger(__name__)
# Configure stdout for unbuffered real-time output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
# Create console with file=stdout and force_terminal for real-time output
console = Console(file=sys.stdout, force_terminal=True, width=None)


class WorkflowCLI:
    """Interactive CLI for workflow testing and execution."""

    def __init__(self) -> None:
        """Initialize the CLI."""
        try:
            self.factory = WorkflowFactory()
        except Exception as e:
            console.print(f"[red]Error loading workflow configuration:[/red] {e}")
            sys.exit(1)

    def display_banner(self) -> None:
        """Display welcome banner."""
        banner = Text()
        banner.append(
            "╔═══════════════════════════════════════════════════════════════╗\n", style="cyan"
        )
        banner.append(
            "║          AgenticFleet - Interactive Workflow CLI               ║\n",
            style="cyan bold",
        )
        banner.append(
            "║          Test and Run Multi-Agent Workflows                    ║\n", style="cyan"
        )
        banner.append(
            "╚═══════════════════════════════════════════════════════════════╝\n", style="cyan"
        )
        console.print(banner)
        console.print()

    def list_workflows(self) -> list[dict[str, Any]]:
        """Get list of available workflows."""
        try:
            return self.factory.list_available_workflows()
        except Exception as e:
            console.print(f"[red]Error listing workflows:[/red] {e}")
            return []

    def display_workflows_table(self) -> None:
        """Display available workflows in a formatted table."""
        workflows = self.list_workflows()

        if not workflows:
            console.print("[yellow]No workflows found in configuration.[/yellow]")
            return

        table = Table(title="Available Workflows", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")
        table.add_column("Agents", justify="right", style="yellow")

        for workflow in workflows:
            table.add_row(
                workflow["id"],
                workflow["name"],
                workflow["description"] or "(no description)",
                str(workflow["agent_count"]),
            )

        console.print(table)
        console.print()

    def display_workflow_config(self, workflow_id: str) -> None:
        """Display detailed configuration for a workflow."""
        try:
            config = self.factory.get_workflow_config(workflow_id)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            return

        # Display workflow info
        info_text = Text()
        info_text.append("ID: ", style="bold")
        info_text.append(config.id, style="cyan")
        info_text.append("\nName: ", style="bold")
        info_text.append(config.name, style="green")
        info_text.append("\nDescription: ", style="bold")
        info_text.append(config.description or "(no description)", style="white")

        console.print(Panel(info_text, title="Workflow Configuration", border_style="cyan"))
        console.print()

        # Display manager configuration
        manager_config = config.manager
        manager_table = Table(
            title="Manager Configuration", show_header=True, header_style="bold yellow"
        )
        manager_table.add_column("Setting", style="cyan")
        manager_table.add_column("Value", style="white")

        manager_table.add_row("Model", manager_config.get("model", "not set"))
        manager_table.add_row(
            "Temperature",
            str(manager_config.get("temperature", "default")),
        )
        manager_table.add_row(
            "Max Tokens",
            str(manager_config.get("max_tokens", "default")),
        )
        manager_table.add_row(
            "Max Round Count",
            str(manager_config.get("max_round_count", "default")),
        )
        manager_table.add_row(
            "Max Stall Count",
            str(manager_config.get("max_stall_count", "default")),
        )
        manager_table.add_row(
            "Max Reset Count",
            str(manager_config.get("max_reset_count", "default")),
        )

        reasoning = manager_config.get("reasoning", {})
        if reasoning:
            manager_table.add_row(
                "Reasoning Effort",
                str(reasoning.get("effort", "default")),
            )
            manager_table.add_row(
                "Reasoning Verbosity",
                str(reasoning.get("verbosity", "default")),
            )

        instructions = manager_config.get("instructions", "")
        if instructions:
            manager_table.add_row(
                "Instructions",
                instructions[:100] + "..." if len(instructions) > 100 else instructions,
            )

        console.print(manager_table)
        console.print()

        # Display agents configuration
        agents_table = Table(
            title="Agents Configuration", show_header=True, header_style="bold green"
        )
        agents_table.add_column("Agent", style="cyan")
        agents_table.add_column("Model", style="yellow")
        agents_table.add_column("Description", style="white")
        agents_table.add_column("Tools", style="magenta")

        for agent_name, agent_config in config.agents.items():
            tools = agent_config.get("tools", [])
            tools_str = (
                ", ".join(tools) if isinstance(tools, list) else str(tools) if tools else "none"
            )
            agents_table.add_row(
                agent_name,
                agent_config.get("model", "not set"),
                agent_config.get("description", "")[:50] or "(no description)",
                tools_str,
            )

        console.print(agents_table)
        console.print()

    async def _process_event(
        self,
        event_type: str,
        data: dict[str, Any],
        tracker: Any,
        current_agent: str | None,
        accumulated_text: dict[str, str],
        status_spinner: Status | None,
    ) -> tuple[str | None, dict[str, str]]:
        """Process a workflow event and update state.

        Returns:
            Updated (current_agent, accumulated_text) tuple
        """
        if event_type == "orchestrator.message":
            # Manager coordination message - show briefly then continue
            msg = data.get("message", "")
            kind = data.get("kind", "unknown")

            # Update stage based on kind
            if kind == "task_ledger":
                tracker.update_stage("Planning")
            elif kind == "progress_ledger":
                tracker.update_stage("Evaluating Progress")

            # Show manager message briefly (simplified for speed)
            console.print()
            console.print(f"[cyan]Manager ({kind}):[/cyan]")
            # Show first 200 chars for speed, full message in debug
            preview = msg[:200] + "..." if len(msg) > 200 else msg
            console.print(f"[dim]{preview}[/dim]")
            console.print()

        elif event_type == "message.delta":
            # Streaming agent output - optimize for real-time
            agent_id = data.get("agent_id", "unknown")
            delta = data.get("delta", "")
            is_complete = data.get("complete", False)

            if agent_id != current_agent:
                if current_agent is not None:
                    console.print()  # New line between agents
                current_agent = agent_id
                tracker.update_agent(agent_id)
                accumulated_text[agent_id] = ""
                # Show agent name immediately
                console.print(f"[bold green][{agent_id}][/bold green] ", end="")
                sys.stdout.flush()

            if delta:
                accumulated_text[agent_id] += delta
                # Write directly to stdout for real-time streaming (unbuffered)
                sys.stdout.write(delta)
                sys.stdout.flush()

            if is_complete:
                console.print()  # New line after complete message
                tracker.update_stage("Agent Complete")

        elif event_type == "message.done":
            # Final result
            result = data.get("result", "")
            tracker.update_stage("Complete")
            console.print()
            console.print("=" * 60, style="bold green")
            # Simplified result display for speed
            console.print("[bold green]Final Result:[/bold green]")
            console.print(result if result else "[dim](no result)[/dim]")
            console.print("=" * 60, style="bold green")
            console.print()

        elif event_type == "error":
            error_msg = data.get("error", "Unknown error")
            tracker.update_stage("Error")
            console.print()
            console.print(f"[bold red]Error:[/bold red] {error_msg}")
            console.print()

        elif event_type == "progress":
            # Progress event - update tracker
            stage = data.get("stage", "")
            agent_id = data.get("agent_id")

            if stage == "planning":
                tracker.update_stage("Planning")
            elif stage == "evaluating":
                tracker.update_stage("Evaluating Progress")
            elif stage == "agent.starting" and agent_id:
                tracker.update_agent(agent_id)
            elif stage == "agent.complete":
                tracker.update_stage("Agent Complete")

            # Update status spinner
            if status_spinner:
                status_spinner.update(tracker.get_status_text())

        elif event_type == "unknown":
            # Log unknown events for debugging
            logger.debug(f"Unknown event type: {event_type}")

        return current_agent, accumulated_text

    class ProgressTracker:
        """Track workflow progress for real-time status updates."""

        def __init__(self) -> None:
            self.current_agent: str | None = None
            self.current_stage: str = "Initializing"
            self.round_number: int = 0
            self.start_time: float = time.time()
            self.event_count: int = 0
            self.last_update_time: float = time.time()

        def update_agent(self, agent_id: str) -> None:
            """Update current agent."""
            self.current_agent = agent_id
            self.current_stage = f"Agent: {agent_id}"
            self.last_update_time = time.time()

        def update_stage(self, stage: str) -> None:
            """Update current stage."""
            self.current_stage = stage
            self.last_update_time = time.time()

        def increment_round(self) -> None:
            """Increment round number."""
            self.round_number += 1
            self.last_update_time = time.time()

        def increment_event(self) -> None:
            """Increment event count."""
            self.event_count += 1

        def get_status_text(self) -> str:
            """Get formatted status text."""
            elapsed = time.time() - self.start_time
            if self.current_agent:
                return f"🔄 {self.current_agent} | Round {self.round_number} | {self.event_count} events | {elapsed:.1f}s"
            return f"⏳ {self.current_stage} | {elapsed:.1f}s"

    async def run_workflow_interactive(self, workflow_id: str, message: str | None = None) -> None:
        """Run a workflow interactively with streaming output."""
        try:
            workflow = self.factory.create_from_yaml(workflow_id)
        except Exception as e:
            console.print(f"[red]Error creating workflow:[/red] {e}")
            return

        # Get user input if not provided
        if message is None:
            console.print("[cyan]Enter your message (or press Ctrl+D to cancel):[/cyan]")
            try:
                message = Prompt.ask("Message", default="")
            except KeyboardInterrupt:
                console.print("\n[yellow]Cancelled.[/yellow]")
                return
            except EOFError:
                console.print("\n[yellow]Cancelled.[/yellow]")
                return

        if not message.strip():
            console.print("[yellow]Empty message, cancelling.[/yellow]")
            return

        console.print()
        console.print(Panel(f"[cyan]{message}[/cyan]", title="Input", border_style="cyan"))
        console.print()
        console.print("[bold green]Starting workflow execution...[/bold green]")
        console.print("[dim]Press Ctrl+C to interrupt[/dim]")
        console.print()

        # Initialize progress tracker
        tracker = self.ProgressTracker()

        # State for tracking streaming output
        current_agent: str | None = None
        accumulated_text: dict[str, str] = {}
        try:
            # Use Status for initial feedback
            with Status(tracker.get_status_text(), spinner="dots", console=console) as status:
                async for event in workflow.run(message):
                    tracker.increment_event()
                    event_type = event.get("type")
                    data = event.get("data", {})

                    # Update status every 100ms or on important events
                    current_time = time.time()
                    if current_time - tracker.last_update_time > 0.1 or event_type in (
                        "orchestrator.message",
                        "message.delta",
                        "message.done",
                    ):
                        status.update(tracker.get_status_text())

                    if event_type == "orchestrator.message":
                        # Manager coordination message - show briefly then continue
                        msg = data.get("message", "")
                        kind = data.get("kind", "unknown")

                        # Update stage based on kind
                        if kind == "task_ledger":
                            tracker.update_stage("Planning")
                        elif kind == "progress_ledger":
                            tracker.update_stage("Evaluating Progress")

                        # Show manager message briefly (simplified for speed)
                        console.print()
                        console.print(f"[cyan]Manager ({kind}):[/cyan]")
                        # Show first 200 chars for speed, full message in debug
                        preview = msg[:200] + "..." if len(msg) > 200 else msg
                        console.print(f"[dim]{preview}[/dim]")
                        console.print()

                    elif event_type == "message.delta":
                        # Streaming agent output - optimize for real-time
                        agent_id = data.get("agent_id", "unknown")
                        delta = data.get("delta", "")
                        is_complete = data.get("complete", False)

                        if agent_id != current_agent:
                            if current_agent is not None:
                                console.print()  # New line between agents
                            current_agent = agent_id
                            tracker.update_agent(agent_id)
                            accumulated_text[agent_id] = ""
                            # Show agent name immediately
                            console.print(f"[bold green][{agent_id}][/bold green] ", end="")
                            sys.stdout.flush()

                        if delta:
                            accumulated_text[agent_id] += delta
                            # Write directly to stdout for real-time streaming (unbuffered)
                            sys.stdout.write(delta)
                            sys.stdout.flush()

                        if is_complete:
                            console.print()  # New line after complete message
                            tracker.update_stage("Agent Complete")

                    elif event_type == "message.done":
                        # Final result
                        result = data.get("result", "")
                        tracker.update_stage("Complete")
                        console.print()
                        console.print("=" * 60, style="bold green")
                        # Simplified result display for speed
                        console.print("[bold green]Final Result:[/bold green]")
                        console.print(result if result else "[dim](no result)[/dim]")
                        console.print("=" * 60, style="bold green")
                        console.print()

                    elif event_type == "error":
                        error_msg = data.get("error", "Unknown error")
                        tracker.update_stage("Error")
                        console.print()
                        console.print(f"[bold red]Error:[/bold red] {error_msg}")
                        console.print()

                    elif event_type == "progress":
                        # Progress event - update tracker
                        stage = data.get("stage", "")
                        agent_id = data.get("agent_id")

                        if stage == "planning":
                            tracker.update_stage("Planning")
                        elif stage == "evaluating":
                            tracker.update_stage("Evaluating Progress")
                        elif stage == "agent.starting" and agent_id:
                            tracker.update_agent(agent_id)
                        elif stage == "agent.complete":
                            tracker.update_stage("Agent Complete")

                        # Update status spinner
                        status.update(tracker.get_status_text())

                    elif event_type == "unknown":
                        # Log unknown events for debugging
                        logger.debug(f"Unknown event type: {event_type}")

                    # Flush after each event for immediate output
                    sys.stdout.flush()

        except KeyboardInterrupt:
            console.print()
            console.print("[yellow]Workflow execution interrupted by user.[/yellow]")
        except Exception as e:
            console.print()
            console.print(
                Panel(
                    f"[red]{e!s}[/red]",
                    title="[bold red]Execution Error[/bold red]",
                    border_style="red",
                )
            )
            logger.exception("Workflow execution failed")

    def interactive_menu(self) -> None:
        """Display interactive menu and handle user choices."""
        while True:
            console.print()
            console.print("[bold cyan]Menu Options:[/bold cyan]")
            console.print("  1. List available workflows")
            console.print("  2. View workflow configuration")
            console.print("  3. Run workflow interactively")
            console.print("  4. Run workflow with custom input")
            console.print("  5. Exit")
            console.print()

            try:
                choice = Prompt.ask(
                    "Select an option", choices=["1", "2", "3", "4", "5"], default="1"
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            except EOFError:
                console.print("\n[yellow]Goodbye![/yellow]")
                break

            if choice == "1":
                self.display_workflows_table()
            elif choice == "2":
                workflows = self.list_workflows()
                if not workflows:
                    continue
                workflow_ids = [w["id"] for w in workflows]
                try:
                    workflow_id = Prompt.ask(
                        "Enter workflow ID",
                        choices=workflow_ids,
                        default=workflow_ids[0] if workflow_ids else None,
                    )
                    self.display_workflow_config(workflow_id)
                except (KeyboardInterrupt, EOFError):
                    continue
            elif choice == "3":
                workflows = self.list_workflows()
                if not workflows:
                    continue
                workflow_ids = [w["id"] for w in workflows]
                try:
                    workflow_id = Prompt.ask(
                        "Enter workflow ID",
                        choices=workflow_ids,
                        default=workflow_ids[0] if workflow_ids else None,
                    )
                    asyncio.run(self.run_workflow_interactive(workflow_id))
                except (KeyboardInterrupt, EOFError):
                    continue
            elif choice == "4":
                workflows = self.list_workflows()
                if not workflows:
                    continue
                workflow_ids = [w["id"] for w in workflows]
                try:
                    workflow_id = Prompt.ask(
                        "Enter workflow ID",
                        choices=workflow_ids,
                        default=workflow_ids[0] if workflow_ids else None,
                    )
                    console.print("[cyan]Enter your message:[/cyan]")
                    message = Prompt.ask("Message")
                    asyncio.run(self.run_workflow_interactive(workflow_id, message))
                except (KeyboardInterrupt, EOFError):
                    continue
            elif choice == "5":
                console.print("[yellow]Goodbye![/yellow]")
                break

    def run(self) -> None:
        """Run the interactive CLI."""
        self.display_banner()
        self.interactive_menu()


def main() -> None:
    """Entry point for workflow CLI."""
    try:
        cli = WorkflowCLI()
        cli.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Fatal error:[/red] {e}")
        logger.exception("CLI error")
        sys.exit(1)
