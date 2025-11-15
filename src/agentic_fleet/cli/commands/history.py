"""History command for exporting workflow history."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from ..runner import WorkflowRunner
from ..utils import init_tracing

console = Console()


def export_history(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file path"),
    ] = Path("workflow_history.json"),
    task: Annotated[str, typer.Option("--task", "-t", help="Task to run before export")] = "",
    model: Annotated[
        str, typer.Option("--model", help="Model to use for task execution")
    ] = "gpt-4.1",
) -> None:
    """Export workflow execution history to a file."""

    async def export() -> None:
        init_tracing()
        runner = WorkflowRunner()
        await runner.initialize_workflow(model=model)

        if task:
            console.print(f"[bold blue]Running task: {task}[/bold blue]")
            await runner.run_without_streaming(task)

        assert runner.workflow is not None, "Workflow not initialized"
        assert runner.workflow.dspy_supervisor is not None, "DSPy supervisor not initialized"

        # Get execution summary
        summary = runner.workflow.dspy_supervisor.get_execution_summary()

        # Add metadata
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "execution_summary": summary,
            "config": {
                "model": runner.workflow.config.dspy_model,
                "compiled": runner.workflow.config.compile_dspy,
                "completion_storage": runner.workflow.config.enable_completion_storage,
                "refinement_threshold": runner.workflow.config.refinement_threshold,
            },
        }

        # Write to file
        with open(output, "w") as f:
            json.dump(export_data, f, indent=2)

        console.print(f"[bold green]✓ Exported history to {output}[/bold green]")

    asyncio.run(export())
