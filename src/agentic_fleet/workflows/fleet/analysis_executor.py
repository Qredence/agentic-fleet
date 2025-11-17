"""Analysis executor for fleet workflow.

Uses DSPySupervisor to analyze tasks and produce AnalysisMessage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework import Executor, WorkflowContext

from ...dspy_modules.supervisor import DSPySupervisor
from ...utils.logger import setup_logger
from .decorators import handler
from .messages import AnalysisMessage, TaskMessage

if TYPE_CHECKING:
    from ..orchestration import SupervisorContext

logger = setup_logger(__name__)


class AnalysisExecutor(Executor):
    """Executor that analyzes tasks using DSPy supervisor."""

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPySupervisor,
        context: SupervisorContext,
    ) -> None:
        """Initialize AnalysisExecutor.

        Args:
            executor_id: Unique executor identifier
            supervisor: DSPy supervisor instance for task analysis
            context: Supervisor context with configuration and state
        """
        super().__init__(id=executor_id)
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

        # Simple-task fast path: for light pipeline profile and obviously short tasks,
        # skip DSPy analysis entirely and fall back to the heuristic analysis. This
        # avoids an extra LM call for trivial requests.
        cfg = self.context.config
        pipeline_profile = getattr(cfg, "pipeline_profile", "full")
        simple_threshold = getattr(cfg, "simple_task_max_words", 40)

        is_simple = self._is_simple_task(task_msg.task, simple_threshold)
        use_light_path = pipeline_profile == "light" and is_simple

        try:
            if use_light_path:
                # Heuristic analysis only; mark as simple in metadata so downstream
                # routing can choose lightweight execution paths.
                analysis_dict = self._fallback_analysis(task_msg.task)
                metadata = {**task_msg.metadata, "simple_mode": True}
            else:
                # Use cached DSPy analysis when available
                cache = self.context.analysis_cache
                cache_key = task_msg.task.strip()
                cached = cache.get(cache_key) if cache is not None else None  # type: ignore[union-attr]

                if cached is not None:
                    logger.info("Using cached DSPy analysis for task")
                    analysis_dict = cached
                else:
                    # Use DSPy supervisor to analyze task (tool-aware when tools exist)
                    analysis_dict = await self._call_with_retry(
                        self.supervisor.analyze_task,
                        task_msg.task,
                        use_tools=True,
                        perform_search=True,
                    )
                    if cache is not None:
                        cache.set(cache_key, analysis_dict)  # type: ignore[union-attr]
                metadata = {**task_msg.metadata, "simple_mode": is_simple}

            # Convert to AnalysisResult
            from ..shared.analysis import analysis_result_from_legacy

            analysis_result = analysis_result_from_legacy(analysis_dict)

            # Create analysis message
            analysis_msg = AnalysisMessage(
                task=task_msg.task,
                analysis=analysis_result,
                metadata=metadata,
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

    def _is_simple_task(self, task: str, max_words: int) -> bool:
        """Heuristic classifier for simple tasks based on word count."""
        if not task:
            return True
        try:
            words = task.strip().split()
            return len(words) <= max_words
        except Exception:
            return False

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
