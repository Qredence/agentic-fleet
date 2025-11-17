"""Quality executor for fleet workflow.

Uses DSPySupervisor to assess quality and produce QualityMessage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_framework import Executor, WorkflowContext

from ...dspy_modules.supervisor import DSPySupervisor
from ...utils.logger import setup_logger
from ...utils.models import RoutingDecision
from .decorators import handler
from .messages import ProgressMessage, QualityMessage

if TYPE_CHECKING:
    from ..orchestration import SupervisorContext

logger = setup_logger(__name__)


class QualityExecutor(Executor):
    """Executor that assesses quality using DSPy supervisor."""

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPySupervisor,
        context: SupervisorContext,
    ) -> None:
        """Initialize QualityExecutor.

        Args:
            executor_id: Unique executor identifier
            supervisor: DSPy supervisor instance for quality assessment
            context: Supervisor context with configuration and state
        """
        super().__init__(id=executor_id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_progress(
        self,
        progress_msg: ProgressMessage,
        ctx: WorkflowContext[QualityMessage],
    ) -> None:
        """Handle progress message and assess quality.

        Args:
            progress_msg: Progress message from previous executor
            ctx: Workflow context for sending messages
        """
        logger.info("Assessing quality...")

        try:
            cfg = self.context.config
            pipeline_profile = getattr(cfg, "pipeline_profile", "full")
            enable_eval = getattr(cfg, "enable_quality_eval", True)

            if pipeline_profile == "light" or not enable_eval:
                # Lightweight path: skip DSPy quality assessment to reduce LM calls.
                from ..shared.models import QualityReport

                quality_report = QualityReport(
                    score=0.0,
                    missing="",
                    improvements="",
                    used_fallback=True,
                )
            else:
                # Use DSPy supervisor to assess quality
                quality_dict = await self._call_with_retry(
                    self.supervisor.assess_quality,
                    requirements=progress_msg.task,
                    results=progress_msg.result,
                )

                # Convert to QualityReport
                from ..shared.quality import quality_report_from_legacy

                quality_report = quality_report_from_legacy(quality_dict)

            # Extract routing from metadata if available
            routing = None
            if "routing" in progress_msg.metadata:
                routing_data = progress_msg.metadata["routing"]
                if isinstance(routing_data, RoutingDecision):
                    routing = routing_data
                elif isinstance(routing_data, dict):
                    routing = RoutingDecision.from_mapping(routing_data)

            # Create quality message
            quality_msg = QualityMessage(
                task=progress_msg.task,
                result=progress_msg.result,
                quality=quality_report,
                routing=routing,
                metadata=progress_msg.metadata,
            )

            logger.info(f"Quality assessment: score={quality_report.score}/10")

            # Send to next executor
            await ctx.send_message(quality_msg)

        except Exception as e:
            logger.exception(f"Quality assessment failed: {e}")
            # Fallback quality
            from ..shared.models import QualityReport

            quality_report = QualityReport(
                score=5.0,
                missing="",
                improvements="",
                used_fallback=True,
            )

            quality_msg = QualityMessage(
                task=progress_msg.task,
                result=progress_msg.result,
                quality=quality_report,
                metadata={**progress_msg.metadata, "used_fallback": True},
            )
            await ctx.send_message(quality_msg)

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
