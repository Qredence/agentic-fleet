"""Progress phase executor.

Split out of `workflows/executors.py` to keep each executor implementation focused.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from agent_framework._workflows import Executor, WorkflowContext

from ...dspy_modules.reasoner import DSPyReasoner
from ...utils.logger import setup_logger
from ...utils.memory import get_process_rss_mb
from ...utils.models import RoutingDecision
from ...utils.resilience import async_call_with_retry
from ...utils.telemetry import optional_span
from ..context import SupervisorContext
from ..models import ExecutionMessage, ProgressMessage, ProgressReport
from .base import handler

logger = setup_logger(__name__)


class ProgressExecutor(Executor):
    """Executor that evaluates progress."""

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPyReasoner,
        context: SupervisorContext,
    ) -> None:
        """Initialize the progress executor."""
        super().__init__(id=executor_id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_execution(
        self,
        execution_msg: ExecutionMessage,
        ctx: WorkflowContext[ProgressMessage],
    ) -> None:
        """
        Evaluate the task's progress after execution and emit a ProgressMessage containing the progress assessment and routing metadata.

        Parameters:
            execution_msg (ExecutionMessage): The execution result to evaluate; its outcome.result is used as the completed work to assess.
            ctx (WorkflowContext[ProgressMessage]): Workflow context used to send the resulting ProgressMessage.

        Behavior:
            - Uses configured DSPy progress evaluation when enabled and not in the "light" pipeline profile; otherwise produces a fallback completion report.
            - Attaches any available routing decision to the emitted message's metadata.
            - On errors, records a `"continue"` progress action with `used_fallback=True` and still emits a ProgressMessage so the workflow can proceed.
        """
        with optional_span(
            "ProgressExecutor.handle_execution", attributes={"task": execution_msg.task}
        ):
            logger.info("Evaluating progress...")
            start_t = perf_counter()
            start_mem_mb = get_process_rss_mb()

            try:
                cfg = self.context.config
                pipeline_profile = getattr(cfg, "pipeline_profile", "full")
                enable_eval = getattr(cfg, "enable_progress_eval", True)

                if pipeline_profile == "light" or not enable_eval:
                    progress_report = ProgressReport(
                        action="complete", feedback="", used_fallback=True
                    )
                    used_fallback = True
                else:
                    retry_attempts = max(1, int(cfg.dspy_retry_attempts))
                    retry_backoff = max(0.0, float(cfg.dspy_retry_backoff_seconds))
                    progress_dict = await async_call_with_retry(
                        self.supervisor.evaluate_progress,
                        original_task=execution_msg.task,
                        completed=execution_msg.outcome.result,
                        status="completion",
                        attempts=retry_attempts,
                        backoff_seconds=retry_backoff,
                    )
                    progress_report = self._to_progress_report(progress_dict)
                    used_fallback = False

                routing = None
                outcome = execution_msg.outcome
                if hasattr(outcome, "routing"):
                    routing = getattr(outcome, "routing", None)
                elif "routing" in execution_msg.metadata:
                    routing_data = execution_msg.metadata["routing"]
                    if isinstance(routing_data, RoutingDecision):
                        routing = routing_data
                    elif isinstance(routing_data, dict):
                        routing = RoutingDecision.from_mapping(routing_data)

                metadata = execution_msg.metadata.copy()
                if routing:
                    metadata["routing"] = routing

                duration = max(0.0, perf_counter() - start_t)
                self.context.latest_phase_timings["progress"] = duration
                self.context.latest_phase_status["progress"] = (
                    "fallback" if used_fallback else "success"
                )

                progress_msg = ProgressMessage(
                    task=execution_msg.task,
                    result=execution_msg.outcome.result,
                    progress=progress_report,
                    metadata=metadata,
                )
                await ctx.send_message(progress_msg)

            except Exception as e:
                # Intentional broad exception handling: Progress evaluation is non-critical.
                # Default to "continue" action to allow workflow to proceed.
                logger.exception(f"Progress evaluation failed: {e}")
                progress_report = ProgressReport(action="continue", feedback="", used_fallback=True)
                self.context.latest_phase_status["progress"] = "failed"
                progress_msg = ProgressMessage(
                    task=execution_msg.task,
                    result=execution_msg.outcome.result,
                    progress=progress_report,
                    metadata={**execution_msg.metadata, "used_fallback": True},
                )
                await ctx.send_message(progress_msg)
            finally:
                end_mem_mb = get_process_rss_mb()
                try:
                    self.context.latest_phase_memory_mb["progress"] = end_mem_mb
                    self.context.latest_phase_memory_delta_mb["progress"] = (
                        end_mem_mb - start_mem_mb
                    )
                except Exception:
                    # Memory metrics are optional and should never fail the workflow.
                    pass

    def _to_progress_report(self, payload: dict[str, Any]) -> ProgressReport:
        """Convert dictionary payload to ProgressReport.

        Validates and normalizes action field to one of the allowed values:
        continue, refine, complete, or escalate.

        Args:
            payload: Dictionary containing progress evaluation data.

        Returns:
            Validated ProgressReport dataclass instance.
        """
        action = str(payload.get("action", "continue") or "continue").strip().lower()
        if action not in {"continue", "refine", "complete", "escalate"}:
            action = "continue"
        return ProgressReport(
            action=action,
            feedback=str(payload.get("feedback", "") or ""),
            used_fallback=bool(payload.get("used_fallback")),
        )
