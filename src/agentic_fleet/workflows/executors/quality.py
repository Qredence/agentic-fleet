"""Quality phase executor.

Split out of `workflows/executors.py` to keep each executor implementation focused.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from agent_framework._workflows import Executor, WorkflowContext

from ...dspy_modules.reasoner import DSPyReasoner
from ...utils.logger import setup_logger
from ...utils.memory import get_process_rss_mb
from ...utils.models import ExecutionMode, RoutingDecision
from ...utils.resilience import async_call_with_retry
from ...utils.telemetry import optional_span
from ..context import SupervisorContext
from ..models import FinalResultMessage, ProgressMessage, QualityMessage, QualityReport
from .base import handler

logger = setup_logger(__name__)


class QualityExecutor(Executor):
    """Executor that assesses quality."""

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPyReasoner,
        context: SupervisorContext,
    ) -> None:
        """Initialize the quality executor."""
        super().__init__(id=executor_id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_progress(
        self,
        progress_msg: ProgressMessage,
        ctx: WorkflowContext[QualityMessage, FinalResultMessage],
    ) -> None:
        """Handle a progress message."""
        with optional_span(
            "QualityExecutor.handle_progress", attributes={"task": progress_msg.task}
        ):
            logger.info("Assessing quality...")
            start_t = perf_counter()
            start_mem_mb = get_process_rss_mb()

            try:
                cfg = self.context.config
                pipeline_profile = getattr(cfg, "pipeline_profile", "full")
                enable_eval = getattr(cfg, "enable_quality_eval", True)

                if pipeline_profile == "light" or not enable_eval:
                    # Use 0.0 to indicate "not evaluated" or missing quality data
                    quality_report = QualityReport(
                        score=0.0, missing="", improvements="", used_fallback=True
                    )
                    used_fallback = True
                else:
                    retry_attempts = max(1, int(cfg.dspy_retry_attempts))
                    retry_backoff = max(0.0, float(cfg.dspy_retry_backoff_seconds))
                    quality_dict = await async_call_with_retry(
                        self.supervisor.assess_quality,
                        requirements=progress_msg.task,
                        results=progress_msg.result,
                        attempts=retry_attempts,
                        backoff_seconds=retry_backoff,
                    )
                    quality_report = self._to_quality_report(quality_dict)
                    used_fallback = False

                routing = None
                if "routing" in progress_msg.metadata:
                    routing_data = progress_msg.metadata["routing"]
                    if isinstance(routing_data, RoutingDecision):
                        routing = routing_data
                    elif isinstance(routing_data, dict):
                        routing = RoutingDecision.from_mapping(routing_data)

                duration = max(0.0, perf_counter() - start_t)
                self.context.latest_phase_timings["quality"] = duration
                self.context.latest_phase_status["quality"] = (
                    "fallback" if used_fallback else "success"
                )

                # Build FinalResultMessage and yield as workflow output
                # This is the terminal executor, so we must yield the final result
                if routing is None:
                    routing = RoutingDecision(
                        task=progress_msg.task,
                        assigned_to=(),
                        mode=ExecutionMode.DELEGATED,
                        subtasks=(progress_msg.task,),
                        tool_requirements=(),
                        confidence=0.0,
                    )

                execution_summary = {}
                if self.context.dspy_supervisor:
                    execution_summary = self.context.dspy_supervisor.get_execution_summary()

                # Inject tool usage into summary for history persistence
                if "tool_usage" in progress_msg.metadata:
                    execution_summary["tool_usage"] = progress_msg.metadata["tool_usage"]

                # Generate narrative if enabled
                if getattr(cfg, "enable_narration", True) and self.context.execution_history:
                    try:
                        narrative = self.supervisor.narrate_events(self.context.execution_history)
                        if narrative:
                            execution_summary["narrative"] = narrative
                    except Exception as e:
                        logger.warning(f"Failed to generate narrative: {e}")

                final_msg = FinalResultMessage(
                    result=progress_msg.result,
                    routing=routing,
                    quality=quality_report,
                    judge_evaluations=[],
                    execution_summary=execution_summary,
                    phase_timings=self.context.latest_phase_timings.copy(),
                    phase_status=self.context.latest_phase_status.copy(),
                    metadata=progress_msg.metadata,
                )
                await ctx.yield_output(final_msg)

            except Exception as e:
                # Intentional broad exception handling: Quality assessment is optional.
                # Return a zero-score fallback to allow workflow completion.
                logger.exception(f"Quality assessment failed: {e}")
                # Use 0.0 to indicate "not evaluated" or missing quality data
                quality_report = QualityReport(
                    score=0.0, missing="", improvements="", used_fallback=True
                )
                self.context.latest_phase_status["quality"] = "failed"

                # Still need to yield output even on failure
                routing = None
                if "routing" in progress_msg.metadata:
                    routing_data = progress_msg.metadata["routing"]
                    if isinstance(routing_data, RoutingDecision):
                        routing = routing_data
                    elif isinstance(routing_data, dict):
                        routing = RoutingDecision.from_mapping(routing_data)

                if routing is None:
                    routing = RoutingDecision(
                        task=progress_msg.task,
                        assigned_to=(),
                        mode=ExecutionMode.DELEGATED,
                        subtasks=(progress_msg.task,),
                        tool_requirements=(),
                        confidence=0.0,
                    )

                final_msg = FinalResultMessage(
                    result=progress_msg.result,
                    routing=routing,
                    quality=quality_report,
                    judge_evaluations=[],
                    execution_summary={},
                    phase_timings=self.context.latest_phase_timings.copy(),
                    phase_status=self.context.latest_phase_status.copy(),
                    metadata={**progress_msg.metadata, "used_fallback": True},
                )
                await ctx.yield_output(final_msg)
            finally:
                end_mem_mb = get_process_rss_mb()
                try:
                    self.context.latest_phase_memory_mb["quality"] = end_mem_mb
                    self.context.latest_phase_memory_delta_mb["quality"] = end_mem_mb - start_mem_mb
                except Exception:
                    # Memory metrics are optional and should never fail the workflow.
                    pass

    def _to_quality_report(self, payload: dict[str, Any]) -> QualityReport:
        """Convert dictionary payload to QualityReport.

        Extracts quality metrics including score, missing elements,
        improvements needed, and optional judge evaluation data.

        Args:
            payload: Dictionary containing quality assessment data.

        Returns:
            Validated QualityReport dataclass instance.
        """
        return QualityReport(
            score=float(payload.get("score", 0.0) or 0.0),
            missing=str(payload.get("missing", "")),
            improvements=str(payload.get("improvements", "")),
            judge_score=payload.get("judge_score"),
            final_evaluation=payload.get("final_evaluation"),
            used_fallback=bool(payload.get("used_fallback")),
        )


# =============================================================================
# DEPRECATED: JudgeRefineExecutor removed from workflow graph in Plan #4
# This class is retained for backwards compatibility but is no longer used.
# The workflow now terminates at QualityExecutor for improved latency.
# =============================================================================
