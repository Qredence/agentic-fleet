"""Bridge Middleware for capturing runtime history and converting to DSPy examples."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any

from ..api.middlewares import ChatMiddleware
from ..utils.history_manager import HistoryManager
from ..utils.logger import setup_logger
from .converters import BridgeConverter

logger = setup_logger(__name__)


class BridgeMiddleware(ChatMiddleware):
    """Middleware that captures workflow execution for offline learning."""

    def __init__(
        self,
        history_manager: HistoryManager,
        dspy_examples_path: str | None = "logs/dspy_examples.jsonl",
    ):
        self.history_manager = history_manager
        self.dspy_examples_path = dspy_examples_path
        self.execution_data: dict[str, Any] = {}

    async def on_start(self, task: str, context: dict[str, Any]) -> None:
        """Initialize execution record."""
        self.execution_data = {
            "workflowId": context.get("workflowId"),
            "task": task,
            "start_time": datetime.now().isoformat(),
            "mode": context.get("mode", "standard"),
            "metadata": context.get("metadata", {}),
        }

    async def on_event(self, event: Any) -> None:
        """Capture intermediate events."""
        # We could capture streaming events here if we want granular history
        pass

    async def on_end(self, result: Any) -> None:
        """Finalize and save execution record."""
        self.execution_data["end_time"] = datetime.now().isoformat()

        # Result is typically a dict from SupervisorWorkflow.run()
        if isinstance(result, dict):
            self.execution_data.update(result)
        else:
            self.execution_data["result"] = str(result)

        try:
            # Save execution history
            await self.history_manager.save_execution_async(self.execution_data)

            # Convert to DSPy example and save asynchronously
            await self._save_dspy_example()

        except Exception as e:
            logger.error(f"Failed to save execution history in middleware: {e}")

    async def on_error(self, error: Exception) -> None:
        """Capture failure."""
        self.execution_data["end_time"] = datetime.now().isoformat()
        self.execution_data["error"] = str(error)
        self.execution_data["status"] = "failed"

        try:
            await self.history_manager.save_execution_async(self.execution_data)
        except Exception as e:
            logger.error(f"Failed to save error history in middleware: {e}")

    async def _save_dspy_example(self) -> None:
        """Convert execution data to DSPy example and save it without blocking the event loop."""
        if not self.dspy_examples_path:
            return

        task = self.execution_data.get("task")
        output = self.execution_data.get("result")

        if not task or not output:
            logger.warning(
                f"Skipping DSPy example: missing task ({bool(task)}) or output ({bool(output)}) "
                f"for workflowId {self.execution_data.get('workflowId')}."
            )
            return

        try:
            # Create a simple example from the result (cheap operation, keep in event loop)
            example = BridgeConverter.thread_to_example(
                messages=[
                    {"role": "user", "content": task},
                    {"role": "assistant", "content": output},
                ],
                task_override=task,
            )

            example_dict = dict(example.items())
            line = json.dumps(example_dict) + "\n"
            path = self.dspy_examples_path
            dir_path = os.path.dirname(path)

            def write_file():
                os.makedirs(dir_path, exist_ok=True)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line)

            # Offload blocking file system operations to a thread
            await asyncio.to_thread(write_file)
        except Exception as e:
            logger.error(f"Failed to save DSPy example: {e}")
