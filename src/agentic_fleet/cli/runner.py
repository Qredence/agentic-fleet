"""Workflow runner for CLI execution.

This module provides the WorkflowRunner class that manages workflow
execution and coordinates with the display system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from ..utils.config_loader import get_agent_model, load_config
from ..utils.error_utils import sanitize_error_message
from ..utils.logger import setup_logger
from ..utils.progress import RichProgressCallback
from ..workflows.config import WorkflowConfig
from ..workflows.supervisor_workflow import create_supervisor_workflow

logger = setup_logger(__name__)


class WorkflowRunner:
    """Manages workflow execution and display."""

    def __init__(self, verbose: bool = False):
        """Initialize workflow runner.

        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.workflow: Any | None = None
        self.console = Console()
        self.current_agents: list[str] = []
        self.progress_callback = RichProgressCallback(console=self.console)

    async def initialize_workflow(
        self,
        compile_dspy: bool = True,
        max_rounds: int = 15,
        model: str | None = None,
        enable_handoffs: bool | None = None,
    ) -> Any:
        """Initialize the workflow with configuration.

        Args:
            compile_dspy: Whether to compile DSPy modules
            max_rounds: Maximum workflow rounds
            model: Override model ID
            enable_handoffs: Enable/disable handoffs

        Returns:
            Initialized workflow instance
        """
        # Load config from YAML
        yaml_config = load_config()

        opt_cfg = yaml_config.get("dspy", {}).get("optimization", {})
        examples_path = opt_cfg.get("examples_path", "data/supervisor_examples.json")
        use_gepa = opt_cfg.get("use_gepa", False)

        # GEPA exclusivity resolution
        auto_choice = opt_cfg.get("gepa_auto")
        full_evals_choice = opt_cfg.get("gepa_max_full_evals")
        metric_calls_choice = opt_cfg.get("gepa_max_metric_calls")

        if auto_choice:
            full_evals_choice = None
            metric_calls_choice = None
        elif full_evals_choice is not None:
            auto_choice = None
            metric_calls_choice = None
        elif metric_calls_choice is not None:
            auto_choice = None
            full_evals_choice = None

        # Determine effective model
        effective_model = model or yaml_config.get("dspy", {}).get("model", "gpt-5-mini")

        # Build optimization options
        reflection_model_value = (
            opt_cfg.get("gepa_reflection_model") or effective_model if use_gepa else None
        )

        if auto_choice is not None:
            final_auto = auto_choice
        elif full_evals_choice is not None or metric_calls_choice is not None:
            final_auto = None
        else:
            final_auto = "light"

        optimization_options: dict[str, Any] = {
            "auto": final_auto,
            "max_full_evals": full_evals_choice,
            "max_metric_calls": metric_calls_choice,
            "reflection_model": reflection_model_value,
            "log_dir": opt_cfg.get("gepa_log_dir", "logs/gepa"),
            "perfect_score": opt_cfg.get("gepa_perfect_score", 1.0),
            "use_history_examples": opt_cfg.get("gepa_use_history_examples", False),
            "history_min_quality": opt_cfg.get("gepa_history_min_quality", 8.0),
            "history_limit": opt_cfg.get("gepa_history_limit", 200),
            "val_split": opt_cfg.get("gepa_val_split", 0.2),
            "seed": opt_cfg.get("gepa_seed", 13),
            "max_bootstrapped_demos": opt_cfg.get("max_bootstrapped_demos", 4),
        }
        if optimization_options.get("reflection_model") is None:
            optimization_options.pop("reflection_model", None)

        # Build WorkflowConfig
        history_file = yaml_config.get("logging", {}).get(
            "history_file", "logs/execution_history.jsonl"
        )
        history_format = "jsonl" if str(history_file).endswith(".jsonl") else "json"

        handoffs_cfg = (
            yaml_config.get("workflow", {}).get("handoffs", {})
            if isinstance(yaml_config.get("workflow"), dict)
            else {}
        )
        handoffs_enabled = (
            enable_handoffs if enable_handoffs is not None else handoffs_cfg.get("enabled", True)
        )

        config = WorkflowConfig(
            max_rounds=max_rounds,
            max_stalls=yaml_config.get("workflow", {}).get("supervisor", {}).get("max_stalls", 3),
            max_resets=yaml_config.get("workflow", {}).get("supervisor", {}).get("max_resets", 2),
            enable_streaming=yaml_config.get("workflow", {})
            .get("supervisor", {})
            .get("enable_streaming", True),
            parallel_threshold=yaml_config.get("workflow", {})
            .get("execution", {})
            .get("parallel_threshold", 3),
            dspy_model=effective_model,
            compile_dspy=compile_dspy,
            refinement_threshold=yaml_config.get("workflow", {})
            .get("quality", {})
            .get("refinement_threshold", 8.0),
            enable_refinement=yaml_config.get("workflow", {})
            .get("quality", {})
            .get("enable_refinement", True),
            judge_threshold=yaml_config.get("workflow", {})
            .get("quality", {})
            .get("judge_threshold", 7.0),
            enable_judge=yaml_config.get("workflow", {})
            .get("quality", {})
            .get("enable_judge", True),
            max_refinement_rounds=yaml_config.get("workflow", {})
            .get("quality", {})
            .get("max_refinement_rounds", 2),
            judge_model=yaml_config.get("workflow", {}).get("quality", {}).get("judge_model"),
            judge_reasoning_effort=yaml_config.get("workflow", {})
            .get("quality", {})
            .get("judge_reasoning_effort", "medium"),
            enable_completion_storage=yaml_config.get("openai", {}).get(
                "enable_completion_storage", False
            ),
            agent_models={
                agent_name.lower(): get_agent_model(yaml_config, agent_name, effective_model)
                for agent_name in ["researcher", "analyst", "writer", "reviewer"]
            },
            agent_temperatures={
                agent_name.lower(): yaml_config.get("agents", {})
                .get(agent_name.lower(), {})
                .get("temperature")
                for agent_name in ["researcher", "analyst", "writer", "reviewer"]
            },
            history_format=history_format,
            examples_path=examples_path,
            dspy_optimizer="gepa" if use_gepa else "bootstrap",
            gepa_options=optimization_options,
            enable_handoffs=handoffs_enabled,
        )

        with self.console.status("[bold green]Initializing DSPy-Enhanced Workflow..."):
            # Note: config is loaded from YAML, but create_supervisor_workflow
            # uses its own config loading. For now, we use the factory function.
            # TODO: Update initialization to accept config parameter
            workflow = await create_supervisor_workflow(compile_dspy=compile_dspy)
            # Set progress callback if workflow supports it
            if hasattr(workflow, "progress_callback"):
                workflow.progress_callback = self.progress_callback

        self.workflow = workflow
        return workflow

    async def run_with_streaming(self, message: str) -> None:
        """Run workflow with streaming display.

        Args:
            message: Task message to process
        """
        if not self.workflow:
            await self.initialize_workflow()

        assert self.workflow is not None, "Workflow initialization failed"

        # Track execution
        start_time = datetime.now()
        current_agent = None
        agent_outputs: dict[str, str] = {}
        reasoning_shown = False
        judge_evaluations: list[dict[str, Any]] = []

        # Display task
        self.console.print(
            Panel(
                Markdown(f"**Task:** {message}"),
                title="[bold blue]🎯 Processing Request",
                border_style="blue",
            )
        )

        # Stream events
        with Live(console=self.console, refresh_per_second=4) as live:
            from typing import Any as _Any

            status_text: _Any = Text()

            try:
                async for event in self.workflow.run_stream(message):
                    event_type = type(event).__name__

                    # Handle WorkflowOutputEvent with final data
                    if hasattr(event, "data") and isinstance(event.data, dict):
                        final_data = event.data

                        # Show reasoning steps if not already shown
                        if not reasoning_shown:
                            execution_summary = final_data.get("execution_summary", {})
                            routing_history = execution_summary.get("routing_history", [])

                            if routing_history:
                                live.stop()
                                self.console.print("\n" + "=" * 80)
                                self.console.print("[bold cyan]🧠 REASONING STEPS[/bold cyan]")
                                self.console.print("=" * 80 + "\n")

                                for i, routing in enumerate(routing_history, 1):
                                    self.console.print(
                                        Panel(
                                            f"[bold]Mode:[/bold] {routing.get('mode', 'unknown')}\n"
                                            f"[bold]Agents:[/bold] {', '.join(routing.get('assigned_to', []))}\n"
                                            f"[bold]Confidence:[/bold] {routing.get('confidence', 0.0):.2f}",
                                            title=f"[bold yellow]Step {i}[/bold yellow]",
                                            border_style="yellow",
                                        )
                                    )
                                reasoning_shown = True
                                live.start()

                        # Collect judge evaluations
                        judge_evals = final_data.get("judge_evaluations", [])
                        if judge_evals:
                            judge_evaluations = judge_evals

                    # Handle different event types
                    if hasattr(event, "agent_id"):
                        current_agent = event.agent_id  # type: ignore[attr-defined]
                        if current_agent not in agent_outputs:
                            agent_outputs[current_agent] = ""

                    if hasattr(event, "text"):
                        # Streaming text from agent
                        if current_agent:
                            agent_outputs[current_agent] += event.text or ""  # type: ignore[attr-defined]
                            status_text = self._format_agent_output(
                                current_agent,
                                agent_outputs[current_agent],
                            )
                            live.update(status_text)

                    elif hasattr(event, "message"):
                        # Complete message from agent
                        if event.message and hasattr(event.message, "text"):  # type: ignore[attr-defined]
                            live.stop()
                            self.console.print(
                                Panel(
                                    event.message.text,  # type: ignore[attr-defined]
                                    title=f"[bold green]✅ {current_agent}[/bold green]",
                                    border_style="green",
                                )
                            )
                            live.start()

                    elif hasattr(event, "data") and self.verbose:
                        # Final result (metadata-only event when verbose)
                        self.console.print(
                            f"[dim]Event: {event_type}[/dim]",
                            style="dim",
                        )

            except Exception as e:
                live.stop()
                sanitized_msg = sanitize_error_message(
                    e, task=message if "message" in locals() else None
                )
                self.console.print(f"[bold red]Error: {sanitized_msg}[/bold red]")
                if self.verbose:
                    logger.exception("Workflow error")

        # Show judge evaluations if available
        if judge_evaluations:
            self.console.print("\n" + "=" * 80)
            self.console.print("[bold magenta]⚖️  QUALITY ASSESSMENTS[/bold magenta]")
            self.console.print("=" * 80 + "\n")

            for i, judge_eval in enumerate(judge_evaluations, 1):
                score = judge_eval.get("score", 0.0)
                reasoning = judge_eval.get("reasoning", "No reasoning provided")

                self.console.print(
                    Panel(
                        f"[bold]Score:[/bold] {score}/10\n\n[bold]Reasoning:[/bold]\n{reasoning}",
                        title=f"[bold magenta]Assessment {i}[/bold magenta]",
                        border_style="magenta",
                    )
                )

        # Display execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        self.console.print(
            f"\n[bold green]⏱️  Total Execution Time: {execution_time:.2f}s[/bold green]\n"
        )

    async def run_without_streaming(self, message: str) -> dict[str, Any]:
        """Run workflow without streaming and return complete result.

        Args:
            message: Task message to process

        Returns:
            Complete workflow result dictionary
        """
        if not self.workflow:
            await self.initialize_workflow()

        assert self.workflow is not None, "Workflow initialization failed"

        with self.console.status("[bold green]Processing..."):
            result = await self.workflow.run(message)

        return result

    def _format_agent_output(self, agent: str, text: str) -> Panel:
        """Format agent output for display.

        Args:
            agent: Agent name
            text: Agent output text

        Returns:
            Formatted Panel for display
        """
        return Panel(
            Text(text),
            title=f"[bold yellow]{agent} (streaming...)[/bold yellow]",
            border_style="yellow",
        )
