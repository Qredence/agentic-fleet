"""Langfuse integration utilities for enhanced tracing and evaluation.

This module provides utilities for:
- Proper trace grouping and context management
- Framework detection (DSPy vs Agent Framework)
- Evaluation support (LLM as judge, custom scores)
- Dashboard metadata and tags
"""

from __future__ import annotations

import contextvars
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Context variables for request-scoped Langfuse attributes
_langfuse_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "langfuse_trace_id", default=None
)
_langfuse_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "langfuse_session_id", default=None
)
_langfuse_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "langfuse_user_id", default=None
)
_langfuse_metadata: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "langfuse_metadata", default=None
)
_langfuse_tags: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "langfuse_tags", default=None
)

try:
    from langfuse import get_client

    _LANGFUSE_AVAILABLE = True

    def get_langfuse_client():
        """Get the Langfuse client instance."""
        return get_client()

    def set_langfuse_context(
        trace_id: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Set Langfuse context variables for current request."""
        if trace_id is not None:
            _langfuse_trace_id.set(trace_id)
        if session_id is not None:
            _langfuse_session_id.set(session_id)
        if user_id is not None:
            _langfuse_user_id.set(user_id)
        if metadata is not None:
            current_metadata = _langfuse_metadata.get() or {}
            new_metadata = {**current_metadata, **metadata}
            _langfuse_metadata.set(new_metadata)
        if tags is not None:
            current_tags = _langfuse_tags.get() or []
            new_tags = [*current_tags, *tags]
            _langfuse_tags.set(new_tags)

    def get_langfuse_context() -> dict[str, Any]:
        """Get current Langfuse context."""
        return {
            "trace_id": _langfuse_trace_id.get(),
            "session_id": _langfuse_session_id.get(),
            "user_id": _langfuse_user_id.get(),
            "metadata": _langfuse_metadata.get() or {},
            "tags": _langfuse_tags.get() or [],
        }

    def create_workflow_trace(
        workflow_id: str,
        task: str,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        mode: str = "standard",
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> Any:
        """Create a top-level trace for a workflow execution.

        Args:
            workflow_id: Unique workflow identifier
            task: The task being executed
            session_id: Optional session ID for grouping related traces
            user_id: Optional user ID
            mode: Workflow mode (standard, handoff, group_chat, etc.)
            metadata: Additional metadata
            tags: Tags for filtering

        Returns:
            Langfuse trace context manager
        """
        trace_metadata = {
            "workflow_id": workflow_id,
            "task": task,
            "mode": mode,
            "framework": "AgenticFleet",
            **(metadata or {}),
        }

        trace_tags = ["workflow", "agentic-fleet", mode, *(tags or [])]

        # Set context variables for our own tracking
        set_langfuse_context(
            trace_id=workflow_id,
            session_id=session_id,
            user_id=user_id,
            metadata=trace_metadata,
            tags=trace_tags,
        )

        # Start an observed span as the root of the trace
        # Use nullcontext since observe() is a decorator, not a context manager
        # The context is set above and will be picked up by @observe decorators
        from contextlib import nullcontext

        return nullcontext()

    def create_dspy_span(
        name: str,
        *,
        module_name: str | None = None,
        signature: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Create a span for a DSPy module call.

        Args:
            name: Span name (e.g., "TaskAnalysis", "TaskRouting")
            module_name: DSPy module name (e.g., "analyzer", "router")
            signature: DSPy signature name
            metadata: Additional metadata

        Returns:
            Langfuse span context manager
        """
        span_metadata = {
            "framework": "DSPy",
            "dspy_module": module_name or name.lower(),
            **(metadata or {}),
        }
        if signature:
            span_metadata["dspy_signature"] = signature

        # Set metadata in context for observe() to pick up
        set_langfuse_context(metadata=span_metadata, tags=["dspy", "reasoning"])
        # Use nullcontext since observe() is a decorator, not a context manager
        # The context is set above and will be picked up by @observe decorators
        from contextlib import nullcontext

        return nullcontext()

    def create_agent_framework_span(
        name: str,
        *,
        agent_name: str | None = None,
        phase: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Create a span for an Agent Framework call.

        Args:
            name: Span name (e.g., "AgentExecution", "ToolCall")
            agent_name: Name of the agent
            phase: Workflow phase (analysis, routing, execution, etc.)
            metadata: Additional metadata

        Returns:
            Langfuse span context manager
        """
        span_metadata = {
            "framework": "Microsoft Agent Framework",
            "agent_framework": True,
            **(metadata or {}),
        }
        if agent_name:
            span_metadata["agent_name"] = agent_name
        if phase:
            span_metadata["phase"] = phase

        span_tags = ["agent-framework", "microsoft"]
        if agent_name:
            span_tags.append(f"agent:{agent_name}")
        if phase:
            span_tags.append(f"phase:{phase}")

        # Set metadata in context for observe() to pick up
        set_langfuse_context(metadata=span_metadata, tags=span_tags)
        # Use nullcontext since observe() is a decorator, not a context manager
        # The context is set above and will be picked up by @observe decorators
        from contextlib import nullcontext

        return nullcontext()

    def score_trace(
        trace_id: str,
        name: str,
        value: float,
        *,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a score to a trace for evaluation.

        Args:
            trace_id: The trace ID to score
            name: Score name (e.g., "quality", "relevance", "accuracy")
            value: Score value (typically 0.0 to 1.0 or 0 to 10)
            comment: Optional comment explaining the score
            metadata: Additional metadata
        """
        try:
            client = get_langfuse_client()
            client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
                **(metadata or {}),
            )
        except Exception as e:
            logger.debug("Failed to add score to trace: %s", e)

    async def llm_as_judge(
        trace_id: str,
        task: str,
        answer: str,
        criteria: str = "accuracy, completeness, and helpfulness",
        *,
        model: str = "gpt-4o-mini",
        score_name: str = "llm_judge_score",
    ) -> float:
        """Use LLM as a judge to evaluate a trace.

        Args:
            trace_id: The trace ID to evaluate
            task: The original task
            answer: The generated answer
            criteria: Evaluation criteria
            model: Model to use for judging
            score_name: Name for the score

        Returns:
            The judge's score (0.0 to 1.0)
        """
        try:
            import dspy

            from agentic_fleet.dspy_modules.answer_quality import AnswerQualitySignature

            # Use DSPy's quality assessor logic if available, or a specialized judger
            # For simplicity in this utility, we'll use a direct LLM call via dspy if possible
            if dspy.settings.lm:
                judge = dspy.ChainOfThought(AnswerQualitySignature)
                prediction = judge(task=task, answer=answer)
                score = float(getattr(prediction, "score", 0.0)) / 10.0  # Normalize to 0-1
                reasoning = getattr(prediction, "reasoning", "No reasoning provided")

                score_trace(
                    trace_id=trace_id,
                    name=score_name,
                    value=score,
                    comment=reasoning,
                    metadata={"model": model, "criteria": criteria},
                )
                return score

            logger.info(f"LLM as judge requested for trace {trace_id} but no LM configured.")
            return 0.0
        except Exception as e:
            logger.debug("Failed to run LLM as judge: %s", e)
            return 0.0

    def get_trace_url(trace_id: str) -> str | None:
        """Get the Langfuse trace URL if possible."""
        try:
            # Most Langfuse Cloud users use this base URL
            # In a real impl, we'd read this from config
            base_url = "https://cloud.langfuse.com"
            # Try to get public key to determine if we are in US or EU if needed,
            # but for now we fallback to standard cloud URL.
            return f"{base_url}/trace/{trace_id}"
        except Exception:
            return None

except ImportError:
    _LANGFUSE_AVAILABLE = False
    logger.debug("Langfuse not available - tracing utilities disabled")

    def get_langfuse_client():
        """Placeholder for get_langfuse_client when Langfuse is unavailable."""
        return None

    def set_langfuse_context(*args: Any, **kwargs: Any) -> None:
        """Placeholder for set_langfuse_context when Langfuse is unavailable."""
        pass

    def get_langfuse_context() -> dict[str, Any]:
        """Placeholder for get_langfuse_context when Langfuse is unavailable."""
        return {}

    def create_workflow_trace(*args: Any, **kwargs: Any) -> Any:
        """Placeholder for create_workflow_trace when Langfuse is unavailable."""
        from contextlib import nullcontext

        return nullcontext()

    def create_dspy_span(*args: Any, **kwargs: Any) -> Any:
        """Placeholder for create_dspy_span when Langfuse is unavailable."""
        from contextlib import nullcontext

        return nullcontext()

    def create_agent_framework_span(*args: Any, **kwargs: Any) -> Any:
        """Placeholder for create_agent_framework_span when Langfuse is unavailable."""
        from contextlib import nullcontext

        return nullcontext()

    def score_trace(*args: Any, **kwargs: Any) -> None:
        """Placeholder for score_trace when Langfuse is unavailable."""
        pass

    def llm_as_judge(*args: Any, **kwargs: Any) -> None:
        """Placeholder for llm_as_judge when Langfuse is unavailable."""
        pass
