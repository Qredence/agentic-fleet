"""Analysis phase executor.

Split out of `workflows/executors.py` to keep each executor implementation focused.
"""

from __future__ import annotations

import re
from dataclasses import replace
from hashlib import sha256
from time import perf_counter
from typing import Any

from agent_framework._workflows import Executor, WorkflowContext

from ...dspy_modules.reasoner import DSPyReasoner
from ...utils.logger import setup_logger
from ...utils.memory import get_process_rss_mb
from ...utils.resilience import async_call_with_retry
from ...utils.telemetry import optional_span
from ..context import SupervisorContext
from ..conversation_context import (
    render_conversation_context,
    render_conversation_context_from_messages,
)
from ..exceptions import ToolError
from ..models import AnalysisMessage, AnalysisResult, TaskMessage
from .base import handler

logger = setup_logger(__name__)

# Fallback analysis step calculation heuristics:
# These values are chosen based on empirical observation of agentic workflow granularity:
# - MIN_STEPS (3): Ensures that even simple tasks are broken down into at least a few actionable steps,
#   preventing under-segmentation and promoting agent reasoning.
# - MAX_STEPS (6): Prevents over-segmentation, which can overwhelm agents and reduce efficiency.
# - WORDS_PER_STEP (40): Based on typical agentic step complexity, 40 words per step balances
#   granularity and cognitive load, producing steps that are neither too broad nor too fine-grained.
MIN_STEPS = 3  # Minimum number of steps for fallback analysis
MAX_STEPS = 6  # Maximum number of steps for fallback analysis
WORDS_PER_STEP = 40  # Number of words per estimated step


class AnalysisExecutor(Executor):
    """Executor that analyzes tasks using DSPy reasoner."""

    # Complexity threshold constants for _fallback_analysis
    COMPLEX_THRESHOLD = 150
    MODERATE_THRESHOLD = 40

    def __init__(
        self,
        executor_id: str,
        supervisor: DSPyReasoner,
        context: SupervisorContext,
    ) -> None:
        """Initialize the analysis executor."""
        super().__init__(id=executor_id)
        self.supervisor = supervisor
        self.context = context

    def _create_fallback_message(self, task: str, metadata: dict[str, Any]) -> AnalysisMessage:
        """Create a fallback analysis message when DSPy analysis fails."""
        fallback_dict = self._fallback_analysis(task)
        analysis_result = self._to_analysis_result(fallback_dict)
        return AnalysisMessage(
            task=task,
            analysis=analysis_result,
            metadata={**metadata, "used_fallback": True},
        )

    @staticmethod
    def _safe_int_setting(cfg: Any, name: str, default: int) -> int:
        """Read an int setting from cfg, tolerating mocks/non-numeric values."""

        value = getattr(cfg, name, None)
        try:
            if value is None:
                return default
            # Avoid accidentally converting unittest.mock objects (e.g., MagicMock) to 1.
            if value.__class__.__module__.startswith("unittest.mock"):
                return default
            return int(value)
        except Exception:
            return default

    @handler
    async def handle_task(
        self,
        task_msg: TaskMessage,
        ctx: WorkflowContext[AnalysisMessage],
    ) -> None:
        """Handle a task message."""
        with optional_span("AnalysisExecutor.handle_task", attributes={"task": task_msg.task}):
            logger.info(f"Analyzing task: {task_msg.task[:100]}...")

            start_t = perf_counter()
            start_mem_mb = get_process_rss_mb()
            cfg = self.context.config
            pipeline_profile = getattr(cfg, "pipeline_profile", "full")
            simple_threshold = getattr(cfg, "simple_task_max_words", 40)

            # Render compact multi-turn conversation context (if available).
            # This is critical for short follow-up/quick-reply inputs.
            thread = getattr(self.context, "conversation_thread", None)
            ctx_max_messages = self._safe_int_setting(cfg, "conversation_context_max_messages", 8)
            ctx_max_chars = self._safe_int_setting(cfg, "conversation_context_max_chars", 4000)
            conversation_context = render_conversation_context(
                thread,
                current_user_input=task_msg.task,
                max_messages=ctx_max_messages,
                max_chars=ctx_max_chars,
            )

            # Fallback: use persisted conversation history if the AgentThread does not expose
            # a local message store (common with service-managed threads).
            if not conversation_context:
                persisted = getattr(self.context, "conversation_history", None) or []
                conversation_context = render_conversation_context_from_messages(
                    list(persisted),
                    current_user_input=task_msg.task,
                    max_messages=ctx_max_messages,
                    max_chars=ctx_max_chars,
                )

            analysis_input = task_msg.task
            if conversation_context:
                analysis_input = (
                    "Conversation context (most recent messages):\n"
                    + conversation_context
                    + "\n\nUser message:\n"
                    + task_msg.task
                    + "\n\nInterpret the user message as a follow-up to the conversation context when plausible. "
                    "If the user message is just a label/selection, infer what it refers to from the prior assistant question."
                )

            is_simple = self._is_simple_task(task_msg.task, simple_threshold)
            use_light_path = pipeline_profile == "light" and is_simple

            try:
                if use_light_path:
                    analysis_dict = self._fallback_analysis(task_msg.task)
                    metadata = {**task_msg.metadata, "simple_mode": True}
                else:
                    cache = self.context.analysis_cache
                    cache_key = task_msg.task.strip()
                    if conversation_context:
                        ctx_hash = sha256(conversation_context.encode("utf-8")).hexdigest()[:12]
                        cache_key = f"{cache_key}::ctx={ctx_hash}"
                    cached = cache.get(cache_key) if cache is not None else None

                    if cached is not None:
                        logger.info("Using cached DSPy analysis for task")
                        analysis_dict = cached
                        self.context.latest_phase_status["analysis"] = "cached"
                    else:
                        retry_attempts = max(1, int(self.context.config.dspy_retry_attempts))
                        retry_backoff = max(
                            0.0, float(self.context.config.dspy_retry_backoff_seconds)
                        )
                        analysis_dict = await async_call_with_retry(
                            self.supervisor.analyze_task,
                            analysis_input,
                            use_tools=True,
                            perform_search=True,
                            attempts=retry_attempts,
                            backoff_seconds=retry_backoff,
                        )
                        if cache is not None:
                            cache.set(cache_key, analysis_dict)
                        self.context.latest_phase_status["analysis"] = "success"
                    # Include reasoning from DSPy analysis in metadata for frontend display
                    metadata = {
                        **task_msg.metadata,
                        "simple_mode": False,
                        "reasoning": analysis_dict.get("reasoning", ""),
                        "intent": analysis_dict.get("intent"),
                    }

                if conversation_context:
                    metadata["conversation_context"] = conversation_context

                # Convert to AnalysisResult
                analysis_result = self._to_analysis_result(analysis_dict)

                # Async search if needed
                if (
                    analysis_result.needs_web_search
                    and analysis_result.search_query
                    and not analysis_result.search_context
                    and not use_light_path
                ):
                    try:
                        search_context = await self.supervisor.perform_web_search_async(
                            analysis_result.search_query
                        )
                        if search_context:
                            analysis_result = replace(
                                analysis_result, search_context=search_context
                            )
                    except TimeoutError:
                        logger.warning(
                            "Async web search timed out for query: %s",
                            analysis_result.search_query,
                        )
                    except ToolError as exc:
                        logger.warning("Async web search tool error: %s", exc)
                    except Exception as exc:
                        logger.warning("Async web search failed: %s", exc)

                # Record timing
                duration = max(0.0, perf_counter() - start_t)
                self.context.latest_phase_timings["analysis"] = duration

                analysis_msg = AnalysisMessage(
                    task=task_msg.task,
                    analysis=analysis_result,
                    metadata=metadata,
                )

                logger.info(
                    f"Analysis complete: complexity={analysis_result.complexity}, "
                    f"steps={analysis_result.steps}, capabilities={analysis_result.capabilities[:3]}"
                )
                await ctx.send_message(analysis_msg)

            except (TimeoutError, ConnectionError) as e:
                logger.warning(
                    f"Analysis failed due to a network or timeout error ({type(e).__name__}): {e}",
                    exc_info=True,
                )
                analysis_msg = self._create_fallback_message(task_msg.task, task_msg.metadata)
                self.context.latest_phase_status["analysis"] = "fallback"
                await ctx.send_message(analysis_msg)

            except Exception as e:
                # Intentional broad exception handling: DSPy/LLM operations and LLM API calls can fail
                # for various transient reasons (e.g., APIError, rate limits, parsing/model errors,
                # or other unexpected exceptions from external libraries). TimeoutError and ConnectionError
                # are handled separately above. We gracefully degrade to heuristic-based analysis to maintain system availability.
                logger.exception(f"Analysis failed with unexpected error ({type(e).__name__}): {e}")
                analysis_msg = self._create_fallback_message(task_msg.task, task_msg.metadata)
                self.context.latest_phase_status["analysis"] = "fallback"
                await ctx.send_message(analysis_msg)
            finally:
                end_mem_mb = get_process_rss_mb()
                try:
                    self.context.latest_phase_memory_mb["analysis"] = end_mem_mb
                    self.context.latest_phase_memory_delta_mb["analysis"] = (
                        end_mem_mb - start_mem_mb
                    )
                except Exception:
                    # Memory metrics are optional and should never fail the workflow.
                    pass

    def _fallback_analysis(self, task: str) -> dict[str, Any]:
        """Perform fallback analysis when DSPy fails.

        Uses simple heuristics based on word count to estimate task
        complexity when the DSPy analyzer is unavailable.

        Args:
            task: The task string to analyze.

        Returns:
            Dictionary with keys: complexity, capabilities, tool_requirements,
            steps, search_context, needs_web_search, search_query.
        """
        word_count = len(task.split())
        complexity = "simple"
        if word_count > self.COMPLEX_THRESHOLD:
            complexity = "complex"
        elif word_count > self.MODERATE_THRESHOLD:
            complexity = "moderate"

        return {
            "complexity": complexity,
            "capabilities": ["general_reasoning"],
            "tool_requirements": [],
            "steps": max(MIN_STEPS, min(MAX_STEPS, word_count // WORDS_PER_STEP + 1)),
            "search_context": "",
            "needs_web_search": False,
            "search_query": "",
        }

    def _to_analysis_result(self, payload: dict[str, Any]) -> AnalysisResult:
        """Convert dictionary payload to AnalysisResult.

        Safely extracts and validates fields from a dictionary,
        providing sensible defaults for missing or invalid values.

        Args:
            payload: Dictionary containing analysis data from DSPy or fallback.

        Returns:
            Validated AnalysisResult dataclass instance.
        """
        complexity = str(payload.get("complexity", "moderate") or "moderate")
        capabilities = [
            cap_s
            for cap_s in (str(cap).strip() for cap in payload.get("capabilities", []))
            if cap_s
        ]
        tool_requirements = [
            tool_s
            for tool_s in (str(tool).strip() for tool in payload.get("tool_requirements", []))
            if tool_s
        ]
        steps_raw = payload.get("steps", 3)
        try:
            steps = int(steps_raw)
        except (TypeError, ValueError):
            steps = 3
        if steps <= 0:
            steps = 3

        return AnalysisResult(
            complexity=complexity,
            capabilities=capabilities or ["general_reasoning"],
            tool_requirements=tool_requirements,
            steps=steps,
            search_context=str(payload.get("search_context", "") or ""),
            needs_web_search=bool(payload.get("needs_web_search")),
            search_query=str(payload.get("search_query", "") or ""),
        )

    def _is_simple_task(self, task: str, max_words: int) -> bool:
        """Check if a task is simple enough for light path.

        Uses pattern matching and word count to identify trivial tasks
        that can bypass the full DSPy analysis pipeline.

        Args:
            task: The task string to evaluate.
            max_words: Maximum word count threshold for simple tasks.

        Returns:
            True if the task qualifies for light-path processing.
        """
        if not task:
            return False
        simple_patterns = [
            r"(?i)^(remember|save)\s+this:?",
            r"(?i)^(hello|hi|hey|greetings)",
            r"(?i)^/help",
        ]
        if any(re.search(p, task) for p in simple_patterns):
            return True
        words = task.strip().split()
        return len(words) <= max_words
