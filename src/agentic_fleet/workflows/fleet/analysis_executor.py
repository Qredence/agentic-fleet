"""Analysis executor for fleet workflow.

Uses DSPySupervisor to analyze tasks and produce AnalysisMessage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework import Executor, WorkflowContext, handler

from ...dspy_modules.supervisor import DSPySupervisor
from ...utils.logger import setup_logger
from .messages import AnalysisMessage, TaskMessage

if TYPE_CHECKING:
    from ..orchestration import SupervisorContext

logger = setup_logger(__name__)


class AnalysisExecutor(Executor):
    """Executor that analyzes tasks using DSPy supervisor."""

    def __init__(
        self,
        id: str,
        supervisor: DSPySupervisor,
        context: SupervisorContext,
    ) -> None:
        """Initialize AnalysisExecutor.

        Args:
            id: Unique executor identifier
            supervisor: DSPy supervisor instance for task analysis
            context: Supervisor context with configuration and state
        """
        super().__init__(id=id)
        self.supervisor = supervisor
        self.context = context

    @handler
    async def handle_task(
        self,
        task_msg: TaskMessage,
        ctx: WorkflowContext[AnalysisMessage],
    ) -> None:
        """Handle task message and produce analysis.

        Args:
            task_msg: Initial task message
            ctx: Workflow context for sending messages
        """
        logger.info(f"Analyzing task: {task_msg.task[:100]}...")

        try:
            # Use DSPy supervisor to analyze task
            analysis_dict = await self._call_with_retry(
                self.supervisor.analyze_task,
                task_msg.task,
                use_tools=True,
                perform_search=True,
            )

            # Convert to AnalysisResult
            from ..shared.analysis import analysis_result_from_legacy

            analysis_result = analysis_result_from_legacy(analysis_dict)

            # Create analysis message
            analysis_msg = AnalysisMessage(
                task=task_msg.task,
                analysis=analysis_result,
                metadata=task_msg.metadata,
            )

            logger.info(
                f"Analysis complete: complexity={analysis_result.complexity}, "
                f"steps={analysis_result.steps}, capabilities={analysis_result.capabilities[:3]}"
            )

            # Send to next executor
            await ctx.send_message(analysis_msg)

        except Exception as e:
            logger.exception(f"Analysis failed: {e}")
            # Fallback analysis
            fallback_dict = self._fallback_analysis(task_msg.task)
            from ..shared.analysis import analysis_result_from_legacy

            analysis_result = analysis_result_from_legacy(fallback_dict)
            analysis_msg = AnalysisMessage(
                task=task_msg.task,
                analysis=analysis_result,
                metadata={**task_msg.metadata, "used_fallback": True},
            )
            await ctx.send_message(analysis_msg)

    def _fallback_analysis(self, task: str) -> dict[str, Any]:
        """Return a safe default analysis when DSPy is unavailable."""
        logger.error("Falling back to heuristic task analysis for task: %s", task[:100])
        word_count = len(task.split())
        complexity = "simple"
        if word_count > 150:
            complexity = "complex"
        elif word_count > 40:
            complexity = "moderate"

        return {
            "complexity": complexity,
            "capabilities": ["general_reasoning"],
            "tool_requirements": [],
            "steps": max(3, min(6, word_count // 40 + 1)),
            "search_context": "",
            "needs_web_search": False,
            "search_query": "",
        }

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
