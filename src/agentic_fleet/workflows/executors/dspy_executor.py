"""DSPy executor.

This module contains `DSPyExecutor`, a generic workflow executor that can run any
compiled DSPy module as part of an agent-framework workflow graph.

It was previously located in `executors_legacy.py` but is not legacy functionality.
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from agent_framework._workflows import Executor, WorkflowContext

from ...utils.logger import setup_logger
from ...utils.memory import get_process_rss_mb
from ...utils.resilience import async_call_with_retry
from ...utils.telemetry import optional_span
from ..context import SupervisorContext
from .base import handler

logger = setup_logger(__name__)


class DSPyExecutor(Executor):
    """Generic Executor that runs a DSPy module.

    Allows placing any compiled DSPy module directly into the workflow graph.
    """

    def __init__(
        self,
        executor_id: str,
        module: Any,  # dspy.Module
        input_mapper: Callable[[Any], dict[str, Any]],
        output_mapper: Callable[[Any, Any], Any],
        context: SupervisorContext,
    ) -> None:
        """Initialize the DSPy executor.

        Args:
            executor_id: Unique ID for the executor.
            module: The DSPy module to execute.
            input_mapper: Function to map input message to module kwargs.
            output_mapper: Function to map module prediction to output message.
            context: Supervisor context.
        """
        super().__init__(id=executor_id)
        self.module = module
        self.input_mapper = input_mapper
        self.output_mapper = output_mapper
        self.context = context

    @handler
    async def handle_message(
        self,
        msg: Any,
        ctx: WorkflowContext[Any],
    ) -> None:
        """Handle a generic message."""
        with optional_span(
            f"DSPyExecutor.{self.id}", attributes={"module": self.module.__class__.__name__}
        ):
            start_t = perf_counter()
            start_mem_mb = get_process_rss_mb()

            try:
                kwargs = self.input_mapper(msg)

                retry_attempts = max(1, int(self.context.config.dspy_retry_attempts))
                retry_backoff = max(0.0, float(self.context.config.dspy_retry_backoff_seconds))

                def _run_module() -> Any:
                    # DSPy modules are callable
                    return self.module(**kwargs)

                prediction = await async_call_with_retry(
                    _run_module,
                    attempts=retry_attempts,
                    backoff_seconds=retry_backoff,
                )

                output_msg = self.output_mapper(msg, prediction)

                duration = max(0.0, perf_counter() - start_t)
                self.context.latest_phase_timings[self.id] = duration
                self.context.latest_phase_status[self.id] = "success"

                end_mem_mb = get_process_rss_mb()
                try:
                    self.context.latest_phase_memory_mb[self.id] = end_mem_mb
                    self.context.latest_phase_memory_delta_mb[self.id] = end_mem_mb - start_mem_mb
                except Exception:
                    # Memory metrics are optional and should never fail the workflow.
                    pass

                await ctx.send_message(output_msg)

            except Exception as e:
                logger.exception(f"DSPy execution failed in {self.id}: {e}")
                self.context.latest_phase_status[self.id] = "failed"
                raise
