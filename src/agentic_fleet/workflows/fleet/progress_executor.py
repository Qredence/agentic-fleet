"""Progress executor for fleet workflow.

Uses DSPySupervisor to evaluate progress and produce ProgressMessage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_framework import Executor, WorkflowContext, handler

from ...dspy_modules.supervisor import DSPySupervisor
from ...utils.logger import setup_logger
from ...utils.models import RoutingDecision
from .messages import ExecutionMessage, ProgressMessage

if TYPE_CHECKING:
    from ..orchestration import SupervisorContext

logger = setup_logger(__name__)


class ProgressExecutor(Executor):
    """Executor that evaluates progress using DSPy supervisor."""

    def __init__(
        self,
        id: str,
        supervisor: DSPySupervisor,
        context: SupervisorContext,
    ) -> None:
        """Initialize ProgressExecutor.

        Args:
            id: Unique executor identifier
            supervisor: DSPy supervisor instance for progress evaluation
            context: Supervisor context with configuration and state
        """
        super().__init__(id=id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_execution(
        self,
        execution_msg: ExecutionMessage,
        ctx: WorkflowContext[ProgressMessage],
    ) -> None:
        """Handle execution message and evaluate progress.

        Args:
            execution_msg: Execution message from previous executor
            ctx: Workflow context for sending messages
        """
        logger.info("Evaluating progress...")

        try:
            # Use DSPy supervisor to evaluate progress
            progress_dict = await self._call_with_retry(
                self.supervisor.evaluate_progress,
                original_task=execution_msg.task,
                completed=execution_msg.outcome.result,
                status="completion",
            )

            # Convert to ProgressReport
            from ..shared.progress import progress_report_from_legacy

            progress_report = progress_report_from_legacy(progress_dict)

            # Extract routing from execution outcome or metadata
            routing = None
            if hasattr(execution_msg.outcome, "routing"):
                routing = execution_msg.outcome.routing  # type: ignore
            elif "routing" in execution_msg.metadata:
                routing_data = execution_msg.metadata["routing"]
                if isinstance(routing_data, RoutingDecision):
                    routing = routing_data
                elif isinstance(routing_data, dict):
                    routing = RoutingDecision.from_mapping(routing_data)

            # Store routing in metadata for downstream executors
            metadata = execution_msg.metadata.copy()
            if routing:
                metadata["routing"] = routing

            # Create progress message
            progress_msg = ProgressMessage(
                task=execution_msg.task,
                result=execution_msg.outcome.result,
                progress=progress_report,
                metadata=metadata,
            )

            logger.info(f"Progress evaluation: action={progress_report.action}")

            # Send to next executor
            await ctx.send_message(progress_msg)

        except Exception as e:
            logger.exception(f"Progress evaluation failed: {e}")
            # Fallback progress
            from ..shared.models import ProgressReport

            progress_report = ProgressReport(
                action="continue",
                feedback="",
                used_fallback=True,
            )

            progress_msg = ProgressMessage(
                task=execution_msg.task,
                result=execution_msg.outcome.result,
                progress=progress_report,
                metadata={**execution_msg.metadata, "used_fallback": True},
            )
            await ctx.send_message(progress_msg)

    async def _call_with_retry(
        self,
        fn,
        *args,
        **kwargs,
    ):
        """Call DSPy function with retry logic."""
        import asyncio

        attempts = max(1, int(self.context.config.dspy_retry_attempts))
        backoff = max(0.0, float(self.context.config.dspy_retry_backoff_seconds))
        last_exc: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    f"DSPy call {getattr(fn, '__name__', repr(fn))} failed on attempt {attempt}/{attempts}: {exc}"
                )
                if attempt < attempts:
                    await asyncio.sleep(backoff * attempt)

        if last_exc:
            raise last_exc
        raise RuntimeError("DSPy call failed without raising an exception")
