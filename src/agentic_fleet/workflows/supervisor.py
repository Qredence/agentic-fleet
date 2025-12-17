"""Supervisor workflow entrypoints.

Consolidated public API and implementation.
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
import time
from collections.abc import AsyncIterable, AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import (
    AgentRunUpdateEvent,
    ExecutorCompletedEvent,
    FileCheckpointStorage,
    InMemoryCheckpointStorage,
    RequestInfoEvent,
    WorkflowOutputEvent,
    WorkflowRunState,
    WorkflowStartedEvent,
    WorkflowStatusEvent,
)

from ..utils.history_manager import HistoryManager
from ..utils.logger import setup_logger
from ..utils.models import ExecutionMode, RoutingDecision, ensure_routing_decision
from ..utils.telemetry import optional_span
from ..utils.tool_registry import ToolRegistry
from ..utils.ttl_cache import SyncTTLCache
from .builder import build_fleet_workflow
from .config import WorkflowConfig
from .context import SupervisorContext
from .handoff import HandoffManager
from .helpers import is_simple_task
from .initialization import initialize_workflow_context
from .models import (
    FinalResultMessage,
    MagenticAgentMessageEvent,
    QualityReport,
    ReasoningStreamEvent,
    TaskMessage,
)

if TYPE_CHECKING:
    from agent_framework._agents import ChatAgent
    from agent_framework._threads import AgentThread
    from agent_framework._workflows import Workflow

    from ..dspy_modules.reasoner import DSPyReasoner

# Type alias for workflow events that can be yielded by run_stream
WorkflowEvent = (
    WorkflowStartedEvent
    | WorkflowStatusEvent
    | WorkflowOutputEvent
    | MagenticAgentMessageEvent
    | ExecutorCompletedEvent
    | ReasoningStreamEvent
    | RequestInfoEvent
)

logger = setup_logger(__name__)

# Request-scoped reasoning effort using contextvars for thread-safe access.
# This allows concurrent requests to have different reasoning_effort values
# without race conditions on shared agent state.
_reasoning_effort_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "reasoning_effort", default=None
)

# Module-level lock and tracking for reasoning effort mutation.
# Used to detect concurrent modifications to shared agent state.
_reasoning_effort_lock = asyncio.Lock()
_active_reasoning_requests: dict[str, str] = {}  # workflow_id -> reasoning_effort


def get_current_reasoning_effort() -> str | None:
    """Get the current request's reasoning effort from contextvar.

    This is the recommended way to access reasoning_effort in a request-scoped manner,
    avoiding race conditions from shared agent state mutation.

    Returns:
        The reasoning effort level for the current request, or None if not set.
    """
    return _reasoning_effort_ctx.get()


def _thread_has_history(thread: Any | None) -> bool:
    """Best-effort check for whether an agent-framework AgentThread has prior messages.

    We intentionally avoid importing/depending on AgentThread internals here so this
    remains compatible across agent-framework versions.
    """

    if thread is None:
        return False

    # Common case: AgentThread supports __len__.
    try:
        return len(thread) > 0  # type: ignore[arg-type]
    except Exception:
        pass

    # agent-framework AgentThread does not implement __len__ but may expose
    # messages via a ChatMessageStore on `message_store`.
    #
    # We keep this best-effort and defensive to remain compatible across
    # agent-framework versions and custom stores.
    store = getattr(thread, "message_store", None)
    if store is None:
        store = getattr(thread, "_message_store", None)
    if store is not None:
        for attr in ("messages", "_messages", "history"):
            msgs = getattr(store, attr, None)
            if msgs is None:
                continue
            try:
                return len(msgs) > 0  # type: ignore[arg-type]
            except Exception:
                continue
        try:
            return len(store) > 0  # type: ignore[arg-type]
        except Exception:
            pass

    # Service-managed threads: if a service thread id is set, treat this as
    # multi-turn context and avoid stateless fast-path.
    service_thread_id = getattr(thread, "service_thread_id", None) or getattr(
        thread, "_service_thread_id", None
    )
    if service_thread_id:
        return True

    # Last-resort: if the thread is initialized, conservatively assume it may
    # have context (better to skip fast-path than ignore history).
    if bool(getattr(thread, "is_initialized", False)):
        return True

    # Common attribute names across thread implementations.
    for attr in ("messages", "history", "_messages"):
        msgs = getattr(thread, attr, None)
        if msgs is None:
            continue
        try:
            return len(msgs) > 0  # type: ignore[arg-type]
        except Exception:
            continue

    # Fallback: try calling methods that might return an iterable of messages.
    for method_name in ("get_messages", "to_messages", "iter_messages"):
        method = getattr(thread, method_name, None)
        if not callable(method):
            continue
        try:
            maybe_msgs = method()
        except TypeError:
            # Method likely requires args we don't know.
            continue
        except Exception:
            continue
        try:
            it = iter(maybe_msgs)  # type: ignore[arg-type]
        except Exception:
            continue
        try:
            next(it)
            return True
        except StopIteration:
            return False
        except Exception:
            continue

    return False


def _materialize_workflow(builder: Workflow | Any) -> Workflow | Any:
    """Return a runnable workflow instance from a builder if needed."""

    build_fn = getattr(builder, "build", None)
    if callable(build_fn):
        return build_fn()
    return builder


class SupervisorWorkflow:
    """Workflow that drives the AgenticFleet orchestration pipeline."""

    def __init__(
        self,
        context: SupervisorContext,
        workflow_runner: Workflow | None = None,
        dspy_supervisor: DSPyReasoner | None = None,
        *,
        agents: dict[str, ChatAgent] | None = None,
        history_manager: HistoryManager | None = None,
        tool_registry: ToolRegistry | None = None,
        handoff: HandoffManager | None = None,
        mode: str = "standard",
        **_: Any,
    ) -> None:
        if not isinstance(context, SupervisorContext):
            raise TypeError("SupervisorWorkflow requires a SupervisorContext instance.")

        self.context = context
        self.config = context.config
        self.workflow = workflow_runner
        self.mode = mode
        # dspy_supervisor is now dspy_reasoner, but we keep the arg name for compat if needed
        # or we can rename it. Let's rename the internal attribute to avoid confusion.
        self.dspy_reasoner = dspy_supervisor or getattr(self.context, "dspy_supervisor", None)
        self.agents = agents or getattr(self.context, "agents", None)
        self.tool_registry = tool_registry or getattr(self.context, "tool_registry", None)
        self.handoff = handoff or getattr(self.context, "handoff", None)
        self.history_manager = history_manager or getattr(self.context, "history_manager", None)

        if self.history_manager is None:
            self.history_manager = HistoryManager()
        if self.tool_registry is None:
            self.tool_registry = ToolRegistry()

        self.enable_handoffs = bool(getattr(self.context, "enable_handoffs", True))
        self.execution_history: list[dict[str, Any]] = []
        self.current_execution: dict[str, Any] = {}

    def _map_mode_to_execution_mode(self, mode: str) -> ExecutionMode:
        """Map runtime mode string to ExecutionMode enum.

        Args:
            mode: Runtime mode string (e.g., 'group_chat', 'handoff', 'standard')

        Returns:
            Corresponding ExecutionMode enum member
        """
        mode_mapping = {
            "group_chat": ExecutionMode.GROUP_CHAT,
            "handoff": ExecutionMode.HANDOFF,
            "discussion": ExecutionMode.DISCUSSION,
            "parallel": ExecutionMode.PARALLEL,
            "sequential": ExecutionMode.SEQUENTIAL,
            "auto": ExecutionMode.AUTO,
        }
        return mode_mapping.get(mode, ExecutionMode.DELEGATED)

    def _get_mode_decision(self, task: str) -> dict[str, str]:
        """Get cached mode decision for a task.

        Caches the result with TTL and size bounds to avoid memory leaks and
        duplicate DSPy calls within the same workflow run.

        Args:
            task: The task string to evaluate

        Returns:
            Dictionary with 'mode' and 'reasoning' keys
        """
        # Initialize bounded TTL cache if needed (max 1024 entries, 5 min TTL)
        if not hasattr(self, "_mode_decision_cache"):
            self._mode_decision_cache: SyncTTLCache[str, dict[str, str]] = SyncTTLCache(
                max_size=1024,
                ttl_seconds=300,
            )

        # Check if we have a cached decision for this task
        cache_key = f"mode_decision_{hash(task)}"
        cached = self._mode_decision_cache.get(cache_key)
        if cached is not None:
            return cached

        # Compute mode decision
        if (
            self.mode == "auto"
            and self.dspy_reasoner
            and hasattr(self.dspy_reasoner, "select_workflow_mode")
        ):
            decision = self.dspy_reasoner.select_workflow_mode(task)
        else:
            decision = {"mode": self.mode, "reasoning": ""}

        # Cache with TTL and return
        self._mode_decision_cache.set(cache_key, decision)
        return decision

    def _should_fast_path(self, task: str) -> bool:
        """Determine if a task should use the fast-path execution.

        Fast-path bypasses the full workflow for simple tasks that can be
        answered directly by the DSPy reasoner without agent delegation.

        Args:
            task: The task string to evaluate

        Returns:
            True if fast-path should be used, False otherwise
        """
        if not self.dspy_reasoner:
            return False

        # Multi-turn: if we already have conversation context, do NOT fast-path.
        # Fast-path is intentionally stateless and would ignore prior turns.
        conversation_thread = getattr(self.context, "conversation_thread", None)
        if _thread_has_history(conversation_thread):
            logger.debug("Fast-path disabled due to existing conversation thread history")
            return False

        # Check auto-mode fast-path detection (uses cached decision)
        if self.mode == "auto":
            decision = self._get_mode_decision(task)
            if decision.get("mode") == "fast_path":
                return True

        # Check simple task heuristic using configured max_words threshold
        simple_task_max_words = getattr(self.config, "simple_task_max_words", 40)
        return is_simple_task(task, max_words=simple_task_max_words)

    async def _handle_fast_path(
        self,
        task: str,
        *,
        mode_reasoning: str | None = None,
    ) -> dict[str, Any]:
        """Handle fast-path execution for simple tasks.

        Args:
            task: The task to execute
            mode_reasoning: Optional reasoning from mode detection

        Returns:
            Standard workflow result dictionary
        """
        # Assertion for type checker - _should_fast_path ensures dspy_reasoner is not None
        assert self.dspy_reasoner is not None

        logger.info(f"Fast Path triggered for task: {task[:50]}...")
        result_text = self.dspy_reasoner.generate_simple_response(task)

        routing = RoutingDecision(
            task=task,
            assigned_to=("FastResponder",),
            mode=self._map_mode_to_execution_mode(self.mode),
            subtasks=(task,),
        )

        metadata: dict[str, Any] = {"fast_path": True}
        if mode_reasoning:
            metadata["mode_reasoning"] = mode_reasoning

        if self.history_manager:
            # History persistence is now handled by BridgeMiddleware
            pass

        return {
            "result": result_text,
            "routing": routing.to_dict(),
            "quality": {"score": 10.0},
            "judge_evaluations": [],
            "execution_summary": {},
            "phase_timings": {},
            "phase_status": {},
            "metadata": metadata,
        }

    async def run(
        self,
        task: str,
        *,
        workflow_id: str | None = None,
        checkpoint_id: str | None = None,
        checkpoint_storage: Any | None = None,
        schedule_quality_eval: bool = True,
    ) -> dict[str, Any]:
        """
        Run the supervisor workflow for a single textual task and return the final result and associated metadata.

        Returns:
            dict: A result dictionary containing the final `result` (text), `routing` decision, `quality` scores,
            `judge_evaluations`, and additional `metadata` and execution details like timing and phase information.

        Raises:
            RuntimeError: If the workflow runner is not initialized.
            RuntimeError: If the workflow produces no outputs.
        """
        with optional_span("SupervisorWorkflow.run", attributes={"task": task, "mode": self.mode}):
            start_time = datetime.now()
            workflow_id = workflow_id or str(uuid4())
            current_mode = self.mode

            # Notify middlewares
            if hasattr(self.context, "middlewares"):
                for mw in self.context.middlewares:
                    await mw.on_start(
                        task,
                        {
                            "workflowId": workflow_id,
                            "mode": current_mode,
                            "start_time": start_time.isoformat(),
                        },
                    )

            # Unified fast-path check (consolidates auto-mode detection + simple task heuristic)
            if self._should_fast_path(task):
                # Use cached decision to avoid duplicate DSPy call
                decision = self._get_mode_decision(task)
                mode_reasoning = decision.get("reasoning")
                result = await self._handle_fast_path(task, mode_reasoning=mode_reasoning)
                if hasattr(self.context, "middlewares"):
                    for mw in self.context.middlewares:
                        await mw.on_end(result)
                return result

            # Dynamic mode switching for auto mode (non-fast-path cases)
            # Uses cached decision from _should_fast_path check
            if self.mode == "auto" and self.dspy_reasoner:
                decision = self._get_mode_decision(task)
                detected_mode_str = decision.get("mode", "standard")

                # Validate against all valid modes first
                valid_modes = (
                    "group_chat",
                    "concurrent",
                    "handoff",
                    "standard",
                    "fast_path",
                )
                if detected_mode_str not in valid_modes:
                    logger.warning(f"Invalid mode '{detected_mode_str}', defaulting to 'standard'")
                    detected_mode_str = "standard"

                # Rebuild workflow only for modes that require different workflow structure
                if detected_mode_str not in ("standard", "fast_path"):
                    logger.info(f"Switching workflow to mode: {detected_mode_str}")
                    workflow_builder = build_fleet_workflow(
                        self.dspy_reasoner,
                        self.context,
                        mode=detected_mode_str,  # type: ignore[arg-type]
                    )
                    self.workflow = _materialize_workflow(workflow_builder)
                    current_mode = detected_mode_str

            if self.workflow is None:
                raise RuntimeError("Workflow runner not initialized.")

            self.current_execution = {
                "workflowId": workflow_id,
                "task": task,
                "start_time": start_time.isoformat(),
                "mode": current_mode,
            }

            logger.info(f"Running fleet workflow for task: {task[:50]}...")

            if current_mode in ("group_chat", "handoff"):
                msg = ChatMessage(role=Role.USER, text=task)
                result = await self._run_workflow(
                    msg,
                    checkpoint_id=checkpoint_id,
                    checkpoint_storage=checkpoint_storage,
                )

                # Handle Handoff/GroupChat result (usually a list of messages or a single message)
                result_text = ""
                if isinstance(result, list):  # List[ChatMessage]
                    # Find the last message
                    if result:
                        last_msg = result[-1]
                        result_text = getattr(last_msg, "text", str(last_msg))
                elif hasattr(result, "content"):
                    result_text = str(result.content)
                else:
                    result_text = str(result)

                # Persist execution history
                self.current_execution.update(
                    {
                        "result": result_text,
                        "routing": {"mode": current_mode},
                        "quality": {"score": 0.0, "pending": True},
                        "end_time": datetime.now().isoformat(),
                    }
                )
                result_dict = {
                    "result": result_text,
                    "routing": {"mode": current_mode},
                    "quality": {"score": 0.0, "pending": True},
                    "judge_evaluations": [],
                    "metadata": {"mode": current_mode},
                }
                if hasattr(self.context, "middlewares"):
                    for mw in self.context.middlewares:
                        await mw.on_end(result_dict)

                if schedule_quality_eval and result_text.strip():
                    try:
                        from agentic_fleet.services.background_evaluation import (
                            schedule_quality_evaluation,
                        )

                        schedule_quality_evaluation(
                            workflow_id=workflow_id,
                            task=task,
                            answer=result_text,
                            history_manager=self.history_manager,
                        )
                    except Exception:
                        pass
                return result_dict

            task_msg = TaskMessage(task)
            result = await self._run_workflow(
                task_msg,
                checkpoint_id=checkpoint_id,
                checkpoint_storage=checkpoint_storage,
            )
            outputs = result.get_outputs() if hasattr(result, "get_outputs") else []
            if not outputs:
                raise RuntimeError("Workflow did not produce any outputs")

            final_msg = outputs[-1]
            if not isinstance(final_msg, FinalResultMessage):
                # Fallback if final message type mismatch (should not happen in standard flow)
                return {"result": str(final_msg)}

            result_dict = self._final_message_to_dict(final_msg)

            # If quality scoring is not available in the pipeline (common when judge is disabled),
            # evaluate quality in the background and update history after the response is returned.
            try:
                score_value = float(result_dict.get("quality", {}).get("score", 0.0) or 0.0)
            except Exception:
                score_value = 0.0
            if (
                schedule_quality_eval
                and score_value <= 0.0
                and result_dict.get("result", "").strip()
            ):
                result_dict.setdefault("quality", {})["pending"] = True

            # Persist execution history for non-streaming runs
            self.current_execution.update(
                {
                    "result": result_dict.get("result"),
                    "routing": result_dict.get("routing"),
                    "quality": result_dict.get("quality"),
                    "execution_summary": result_dict.get("execution_summary", {}),
                    "phase_timings": result_dict.get("phase_timings", {}),
                    "phase_status": result_dict.get("phase_status", {}),
                    "metadata": result_dict.get("metadata", {}),
                    "end_time": datetime.now().isoformat(),
                }
            )

            if hasattr(self.context, "middlewares"):
                for mw in self.context.middlewares:
                    await mw.on_end(result_dict)

            if (
                schedule_quality_eval
                and score_value <= 0.0
                and result_dict.get("result", "").strip()
            ):
                try:
                    from agentic_fleet.services.background_evaluation import (
                        schedule_quality_evaluation,
                    )

                    schedule_quality_evaluation(
                        workflow_id=workflow_id,
                        task=task,
                        answer=str(result_dict.get("result") or ""),
                        history_manager=self.history_manager,
                    )
                except Exception:
                    pass

            return result_dict

    def _resolve_checkpoint_storage(
        self,
        *,
        checkpoint_id: str | None,
        checkpoint_storage: Any | None,
    ) -> Any | None:
        """Resolve the agent-framework CheckpointStorage to use for a given run.

        If a storage is provided explicitly, it wins. Otherwise, if checkpointing is
        requested (checkpoint_id is not None), we default to a file-based storage
        rooted at `.var/checkpoints`.

        This keeps checkpointing opt-in and avoids impacting existing callers.
        """

        if checkpoint_storage is not None:
            return checkpoint_storage

        if checkpoint_id is None:
            return None

        # Allow contexts/configs to inject their own storage implementation.
        injected = getattr(self.context, "checkpoint_storage", None)
        if injected is not None:
            return injected

        # Default file-based storage under .var/ (repo convention).
        checkpoint_dir = getattr(self.config, "checkpoint_dir", None) or ".var/checkpoints"
        try:
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning(
                "Failed to create checkpoint_dir=%s (%s); falling back to in-memory checkpointing",
                checkpoint_dir,
                exc,
            )
            checkpoint_dir = None

        try:
            if checkpoint_dir:
                return FileCheckpointStorage(checkpoint_dir)
            return InMemoryCheckpointStorage()
        except Exception as exc:  # pragma: no cover - environment / filesystem edge
            logger.warning("Checkpointing unavailable (could not initialize storage): %s", exc)
            return None

    async def _run_workflow(
        self,
        message: Any,
        *,
        checkpoint_id: str | None,
        checkpoint_storage: Any | None,
        include_status_events: bool | None = None,
    ) -> Any:
        """Run the underlying agent-framework workflow with optional checkpointing.

        Uses keyword args when supported, with a safe fallback for older builds.
        """

        if self.workflow is None:
            raise RuntimeError("Workflow runner not initialized.")

        storage = self._resolve_checkpoint_storage(
            checkpoint_id=checkpoint_id,
            checkpoint_storage=checkpoint_storage,
        )

        run_fn = getattr(self.workflow, "run", None)
        if not callable(run_fn):
            raise RuntimeError("Workflow runner does not support run().")

        # agent-framework semantics:
        # - message != None  => new run (checkpoint_id must be omitted)
        # - message == None  => resume (checkpoint_id required)
        if message is not None and checkpoint_id is not None:
            logger.debug(
                "Ignoring checkpoint_id for new run (checkpoint_id=%s)",
                checkpoint_id,
            )

        kwargs: dict[str, Any] = {}
        if checkpoint_id is not None and message is None:
            kwargs["checkpoint_id"] = checkpoint_id
        if storage is not None:
            kwargs["checkpoint_storage"] = storage
        if include_status_events is not None:
            kwargs["include_status_events"] = include_status_events

        try:
            result = run_fn(message, **kwargs)
        except TypeError:
            # Older versions may not accept checkpoint kwargs.
            result = run_fn(message)

        if inspect.isawaitable(result):
            return await result
        return result

    async def _run_workflow_stream(
        self,
        message: Any,
        *,
        checkpoint_id: str | None,
        checkpoint_storage: Any | None,
    ) -> AsyncIterator[Any]:
        """Stream events from the underlying workflow with optional checkpointing.

        agent-framework 1.0.0b251211+ supports kw-only `checkpoint_id` and
        `checkpoint_storage`. This helper passes those kwargs when requested,
        while remaining compatible with older versions.
        """

        if self.workflow is None:
            raise RuntimeError("Workflow runner not initialized.")

        storage = self._resolve_checkpoint_storage(
            checkpoint_id=checkpoint_id,
            checkpoint_storage=checkpoint_storage,
        )

        run_stream_fn = getattr(self.workflow, "run_stream", None)
        if not callable(run_stream_fn):
            raise RuntimeError("Workflow runner does not support run_stream().")

        # agent-framework semantics:
        # - message != None  => new run (checkpoint_id must be omitted)
        # - message == None  => resume (checkpoint_id required)
        if message is not None and checkpoint_id is not None:
            logger.debug(
                "Ignoring checkpoint_id for new streaming run (checkpoint_id=%s)",
                checkpoint_id,
            )

        kwargs: dict[str, Any] = {}
        if checkpoint_id is not None and message is None:
            kwargs["checkpoint_id"] = checkpoint_id
        if storage is not None:
            kwargs["checkpoint_storage"] = storage

        try:
            stream = cast(AsyncIterable[Any], run_stream_fn(message, **kwargs))
        except TypeError:
            stream = cast(AsyncIterable[Any], run_stream_fn(message))

        async for event in stream:
            yield event

    async def send_workflow_responses(self, responses: dict[str, Any]) -> None:
        """Send HITL responses back into an in-flight agent-framework workflow.

        In agent-framework 1.0+, workflows and orchestrations can emit request events
        (e.g., tool approval, user input) and pause until the host sends responses.
        This helper forwards responses to the underlying workflow runner using the
        best available API.

        Args:
            responses: Mapping of request_id -> response payload.

        Raises:
            RuntimeError: If no workflow runner is initialized or it does not support
                receiving responses.
        """
        if self.workflow is None:
            raise RuntimeError("Workflow runner not initialized.")

        send_fn = getattr(self.workflow, "send_responses_streaming", None)
        if not callable(send_fn):
            send_fn = getattr(self.workflow, "send_responses", None)

        if not callable(send_fn):
            raise RuntimeError(
                "Underlying workflow does not support send_responses_streaming/send_responses. "
                "Upgrade agent-framework and ensure the workflow is request/response capable."
            )

        result = send_fn(responses)
        if inspect.isawaitable(result):
            await result

    def _handle_agent_run_update(
        self, event: AgentRunUpdateEvent
    ) -> ReasoningStreamEvent | MagenticAgentMessageEvent | None:
        """
        Convert an AgentRunUpdateEvent into a streaming event representing either reasoning deltas or an agent message.

        Processes the event's `run.delta` safely: if the delta's type indicates reasoning and contains text, returns a `ReasoningStreamEvent` with that reasoning and the agent id; if the delta contains textual content, returns a `MagenticAgentMessageEvent` wrapping a `ChatMessage` with role `Role.ASSISTANT` (joining list content when present); returns `None` when no usable delta or content is available.

        Parameters:
            event (AgentRunUpdateEvent): The agent run update event to convert.

        Returns:
            ReasoningStreamEvent | MagenticAgentMessageEvent | None: `ReasoningStreamEvent` when a reasoning delta is present, `MagenticAgentMessageEvent` when textual content is present, or `None` if no convertible content exists.
        """
        run_obj = getattr(event, "run", None)
        if not (run_obj and hasattr(run_obj, "delta")):
            return None

        delta = getattr(run_obj, "delta", None)
        if delta is None:
            return None

        # Check for reasoning content (GPT-5 series)
        if hasattr(delta, "type") and "reasoning" in str(getattr(delta, "type", "")):
            reasoning_text = getattr(delta, "delta", "")
            if reasoning_text:
                agent_id = getattr(run_obj, "agent_id", "unknown")
                return ReasoningStreamEvent(reasoning=reasoning_text, agent_id=agent_id)
            return None

        # Extract text content for regular messages
        text = ""
        if hasattr(delta, "content") and delta.content:
            if isinstance(delta.content, list):
                text = "".join(str(part) for part in delta.content)
            else:
                text = str(delta.content)

        if text:
            agent_id = getattr(run_obj, "agent_id", "unknown")
            mag_msg = ChatMessage(role=Role.ASSISTANT, text=text)
            return MagenticAgentMessageEvent(agent_id=agent_id, message=mag_msg)

        return None

    async def _apply_reasoning_effort(self, reasoning_effort: str | None, workflow_id: str) -> None:
        """Apply reasoning effort via thread-safe contextvar (concurrency-safe).

        This method sets reasoning_effort using two thread-safe mechanisms:
        1. Sets the contextvar for request-scoped access (preferred, thread-safe)
        2. Stores reasoning_effort in self.context for strategy access

        Callers should read reasoning_effort via:
        - `get_current_reasoning_effort()` (contextvar - preferred)
        - `context.reasoning_effort` (request-scoped)

        Note: Previously this method also mutated shared agent chat_client state,
        which caused race conditions in concurrent requests. That behavior has been
        removed. If reasoning_effort needs to be applied to API calls, it should
        be done at call time by reading from the contextvar.

        Args:
            reasoning_effort: Reasoning effort level ("minimal", "medium", "maximal").
                Must match API schema values defined in ChatRequest.
            workflow_id: Unique identifier for this workflow execution, used for
                tracking active requests.
        """
        # 1. Set contextvar for thread-safe request-scoped access
        _reasoning_effort_ctx.set(reasoning_effort)

        # 2. Store in context for strategies to access
        self.context.reasoning_effort = reasoning_effort

        if not reasoning_effort:
            return

        # 3. Track active requests for debugging/monitoring
        async with _reasoning_effort_lock:
            _active_reasoning_requests[workflow_id] = reasoning_effort

        logger.debug(
            f"Applied reasoning_effort={reasoning_effort} via contextvar for workflow {workflow_id}"
        )

    def _cleanup_reasoning_effort_tracking(self, workflow_id: str) -> None:
        """Remove workflow from active reasoning effort tracking.

        Called at the end of run_stream to clean up tracking state.
        """
        _active_reasoning_requests.pop(workflow_id, None)

    async def run_stream(
        self,
        task: str | None,
        *,
        workflow_id: str | None = None,
        reasoning_effort: str | None = None,
        thread: AgentThread | None = None,
        conversation_history: list[Any] | None = None,
        checkpoint_id: str | None = None,
        checkpoint_storage: Any | None = None,
        schedule_quality_eval: bool = True,
    ) -> AsyncIterator[Any]:
        """
        Execute the workflow for a single task and stream WorkflowEvent objects representing progress and results.

        This coroutine yields status updates, intermediate agent messages, reasoning deltas, and a final output event. It updates internal execution state, notifies configured middlewares on start and end, and supports an optional reasoning effort override and conversation thread context. If a fast-path responder is applicable, it yields fast-path events and returns early.

        Parameters:
            task (str): The task prompt to execute.
            reasoning_effort (str | None): Optional override; must be one of "minimal", "medium", or "maximal". An invalid value yields a FAILED status and terminates the stream.
            thread (AgentThread | None): Optional multi-turn conversation context to store in the workflow context.

        Yields:
            Any: Events emitted during execution. Most callers should expect a mix of
            agent-framework workflow events (status/output/request) and AgenticFleet
            wrapper events (agent messages/reasoning deltas).

        Raises:
            RuntimeError: If the workflow runner is not initialized.
        """
        task_text = task or ""
        is_resume = task is None
        if is_resume and checkpoint_id is None:
            raise ValueError("Resume requires checkpoint_id when task is None")

        task_for_metadata = task_text
        if is_resume:
            # Avoid leaking large/unsafe ids; checkpoint ids are usually short, but still sanitize.
            task_for_metadata = f"[resume:{checkpoint_id}]"

        with optional_span(
            "SupervisorWorkflow.run_stream",
            attributes={"task": task_for_metadata, "mode": self.mode, "is_resume": is_resume},
        ):
            if is_resume:
                logger.info(
                    "Resuming fleet workflow (streaming) from checkpoint: %s",
                    str(checkpoint_id)[:50],
                )
            else:
                logger.info(f"Running fleet workflow (streaming) for task: {task_text[:50]}...")

            # Store thread in context for strategies to use
            self.context.conversation_thread = thread
            # Store persisted conversation history for context rendering (best-effort).
            try:
                self.context.conversation_history = list(conversation_history or [])
            except Exception as e:
                logger.warning(
                    "Failed to convert conversation_history to list (value: %r): %s",
                    conversation_history,
                    e,
                )
                self.context.conversation_history = []
            workflow_id = workflow_id or str(uuid4())
            current_mode = self.mode

            # Apply reasoning effort override if provided
            if reasoning_effort:
                if reasoning_effort not in ("minimal", "medium", "maximal"):
                    logger.warning(
                        f"Invalid reasoning_effort value: {reasoning_effort}. Expected minimal, medium, or maximal."
                    )
                    yield WorkflowStatusEvent(
                        state=WorkflowRunState.FAILED,
                        data={
                            "message": f"Invalid reasoning_effort: {reasoning_effort}. Must be minimal, medium, or maximal."
                        },
                    )
                    # Notify middlewares of termination if present
                    if hasattr(self.context, "middlewares"):
                        for mw in self.context.middlewares:
                            await mw.on_end(
                                task_for_metadata,
                                {
                                    "workflowId": workflow_id,
                                    "mode": current_mode,
                                    "reasoning_effort": reasoning_effort,
                                    "end_time": datetime.now().isoformat(),
                                    "status": "FAILED",
                                },
                            )
                    # Yield a terminal event to signal end of stream
                    yield WorkflowStatusEvent(
                        state=WorkflowRunState.IDLE,
                        data={"message": "Workflow terminated due to invalid reasoning_effort."},
                    )
                    return
                logger.info(f"Applying reasoning_effort={reasoning_effort} for this request")
                await self._apply_reasoning_effort(reasoning_effort, workflow_id)

            # Notify middlewares
            if hasattr(self.context, "middlewares"):
                for mw in self.context.middlewares:
                    await mw.on_start(
                        task_for_metadata,
                        {
                            "workflowId": workflow_id,
                            "mode": current_mode,
                            "reasoning_effort": reasoning_effort,
                            "start_time": datetime.now().isoformat(),
                            "is_resume": is_resume,
                            "checkpoint_id": checkpoint_id if is_resume else None,
                        },
                    )

            # Start timing for observability
            workflow_start_time = time.time()
            logger.info(
                f"[Workflow {workflow_id}] Starting execution for task: {task_for_metadata[:80]}..."
            )

            # Unified fast-path check for streaming (not applicable for resume)
            if not is_resume and self._should_fast_path(task_text):
                async for event in self._yield_fast_path_events(task_text):
                    yield event
                duration = time.time() - workflow_start_time
                logger.info(f"[Workflow {workflow_id}] Fast-path completed in {duration:.2f}s")
                return

            if self.workflow is None:
                raise RuntimeError("Workflow runner not initialized.")

            self.current_execution = {
                "workflowId": workflow_id,
                "task": task_for_metadata,
                "start_time": datetime.now().isoformat(),
            }

            # Emit initial status event immediately so frontend knows workflow started
            yield WorkflowStatusEvent(
                state=WorkflowRunState.IN_PROGRESS,
                data={
                    "message": (
                        "Workflow resume started" if is_resume else "Workflow execution started"
                    ),
                    "workflow_id": workflow_id,
                    "mode": current_mode,
                    "is_resume": is_resume,
                    "checkpoint_id": checkpoint_id if is_resume else None,
                },
            )

            final_msg = None
            saw_output_event = False
            should_schedule_quality_eval = False
            try:
                if current_mode in ("group_chat", "handoff"):
                    msg = None if is_resume else ChatMessage(role=Role.USER, text=task_text)
                    async for event in self._run_workflow_stream(
                        msg,
                        checkpoint_id=checkpoint_id,
                        checkpoint_storage=checkpoint_storage,
                    ):
                        # Surface MagenticAgentMessageEvent from executors (agent.start, agent.output, etc.)
                        if isinstance(event, MagenticAgentMessageEvent):
                            yield event
                        elif isinstance(event, AgentRunUpdateEvent):
                            converted = self._handle_agent_run_update(event)
                            if converted is not None:
                                yield converted
                                if isinstance(converted, ReasoningStreamEvent):
                                    continue

                        elif isinstance(event, RequestInfoEvent):
                            # Surface request events so the API/websocket layer can drive HITL.
                            # (e.g., tool approval, user input, plan review)
                            yield event

                        elif isinstance(event, WorkflowOutputEvent):
                            saw_output_event = True
                            data = getattr(event, "data", None)

                            # If we already have a structured FinalResultMessage, normalize
                            # to the list[ChatMessage] format expected by downstream mappers.
                            if isinstance(data, FinalResultMessage):
                                final_msg = data
                                yield WorkflowOutputEvent(
                                    data=self._create_output_event_data(final_msg),
                                    source_executor_id=current_mode,
                                )
                                continue

                            # Legacy list[ChatMessage] output.
                            if isinstance(data, list) and data and isinstance(data[0], ChatMessage):
                                last_msg = data[-1]
                                execution_mode = self._map_mode_to_execution_mode(current_mode)
                                final_msg = FinalResultMessage(
                                    result=last_msg.text,
                                    routing=RoutingDecision(
                                        task=task_for_metadata,
                                        assigned_to=(current_mode,),
                                        mode=execution_mode,
                                        subtasks=(task_for_metadata,),
                                    ),
                                    quality=QualityReport(score=0.0),
                                    judge_evaluations=[],
                                    execution_summary={},
                                    phase_timings={},
                                    phase_status={},
                                    metadata={"mode": current_mode, "legacy_list_output": True},
                                )
                                yield WorkflowOutputEvent(
                                    data=self._create_output_event_data(final_msg),
                                    source_executor_id=current_mode,
                                )
                                continue

                            # AgentRunResponse-like: capture text so we don't trigger fallback.
                            result_text = ""
                            if data is not None and hasattr(data, "messages"):
                                msgs = list(getattr(data, "messages", []) or [])
                                if msgs:
                                    last_msg = msgs[-1]
                                    result_text = getattr(last_msg, "text", str(last_msg)) or str(
                                        last_msg
                                    )
                            elif data is not None and hasattr(data, "result"):
                                result_text = str(getattr(data, "result", "") or "")
                            elif data is not None:
                                result_text = str(data)

                            if result_text and final_msg is None:
                                execution_mode = self._map_mode_to_execution_mode(current_mode)
                                final_msg = FinalResultMessage(
                                    result=result_text,
                                    routing=RoutingDecision(
                                        task=task_for_metadata,
                                        assigned_to=(current_mode,),
                                        mode=execution_mode,
                                        subtasks=(task_for_metadata,),
                                    ),
                                    quality=QualityReport(score=0.0),
                                    judge_evaluations=[],
                                    execution_summary={},
                                    phase_timings={},
                                    phase_status={},
                                    metadata={
                                        "mode": current_mode,
                                        "workflow_output_unwrapped": True,
                                    },
                                )

                            # Let downstream mapping handle modern WorkflowOutputEvent shapes.
                            yield event
                else:
                    task_msg = None if is_resume else TaskMessage(task_text)
                    async for event in self._run_workflow_stream(
                        task_msg,
                        checkpoint_id=checkpoint_id,
                        checkpoint_storage=checkpoint_storage,
                    ):
                        # Surface MagenticAgentMessageEvent from executors (agent.start, agent.output, etc.)
                        # and ExecutorCompletedEvent for phase completions
                        if isinstance(event, (MagenticAgentMessageEvent, ExecutorCompletedEvent)):
                            yield event
                        elif isinstance(event, AgentRunUpdateEvent):
                            converted = self._handle_agent_run_update(event)
                            if converted is not None:
                                yield converted
                                if isinstance(converted, ReasoningStreamEvent):
                                    continue
                        elif isinstance(event, RequestInfoEvent):
                            yield event
                        elif isinstance(event, WorkflowOutputEvent):
                            saw_output_event = True
                            if hasattr(event, "data"):
                                data = event.data
                                if isinstance(data, FinalResultMessage):
                                    final_msg = data
                                    # Convert to list[ChatMessage] for consistency with new format
                                    yield WorkflowOutputEvent(
                                        data=self._create_output_event_data(data),
                                        source_executor_id=getattr(
                                            event, "source_executor_id", "workflow"
                                        ),
                                    )
                                    continue
                                elif isinstance(data, dict) and "result" in data:
                                    final_msg = self._dict_to_final_message(data)
                                    yield WorkflowOutputEvent(
                                        data=self._create_output_event_data(final_msg),
                                        source_executor_id=getattr(
                                            event, "source_executor_id", "workflow"
                                        ),
                                    )
                                    continue
                                elif isinstance(data, list) and data:
                                    # Handle legacy list[ChatMessage] format from strategies
                                    last_msg = data[-1]
                                    text = getattr(last_msg, "text", str(last_msg))
                                    execution_mode = self._map_mode_to_execution_mode(current_mode)
                                    final_msg = FinalResultMessage(
                                        result=text,
                                        routing=RoutingDecision(
                                            task=task_for_metadata,
                                            assigned_to=(),
                                            mode=execution_mode
                                            if execution_mode != ExecutionMode.GROUP_CHAT
                                            and execution_mode != ExecutionMode.HANDOFF
                                            else ExecutionMode.SEQUENTIAL,
                                            subtasks=(),
                                        ),
                                        quality=QualityReport(score=0.0),
                                        judge_evaluations=[],
                                        execution_summary={},
                                        phase_timings={},
                                        phase_status={},
                                        metadata={"legacy_list_output": True},
                                    )
                                elif data is not None and hasattr(data, "messages"):
                                    # AgentRunResponse-like payload (framework 1.0+)
                                    msgs = list(getattr(data, "messages", []) or [])
                                    if msgs:
                                        last_msg = msgs[-1]
                                        text = getattr(last_msg, "text", str(last_msg)) or str(
                                            last_msg
                                        )
                                        execution_mode = self._map_mode_to_execution_mode(
                                            current_mode
                                        )
                                        final_msg = FinalResultMessage(
                                            result=text,
                                            routing=RoutingDecision(
                                                task=task_for_metadata,
                                                assigned_to=(),
                                                mode=execution_mode
                                                if execution_mode != ExecutionMode.GROUP_CHAT
                                                and execution_mode != ExecutionMode.HANDOFF
                                                else ExecutionMode.SEQUENTIAL,
                                                subtasks=(),
                                            ),
                                            quality=QualityReport(score=0.0),
                                            judge_evaluations=[],
                                            execution_summary={},
                                            phase_timings={},
                                            phase_status={},
                                            metadata={"workflow_output_unwrapped": True},
                                        )
                                elif data is not None and hasattr(data, "result"):
                                    text = str(getattr(data, "result", "") or "")
                                    if text:
                                        execution_mode = self._map_mode_to_execution_mode(
                                            current_mode
                                        )
                                        final_msg = FinalResultMessage(
                                            result=text,
                                            routing=RoutingDecision(
                                                task=task_for_metadata,
                                                assigned_to=(),
                                                mode=execution_mode
                                                if execution_mode != ExecutionMode.GROUP_CHAT
                                                and execution_mode != ExecutionMode.HANDOFF
                                                else ExecutionMode.SEQUENTIAL,
                                                subtasks=(),
                                            ),
                                            quality=QualityReport(score=0.0),
                                            judge_evaluations=[],
                                            execution_summary={},
                                            phase_timings={},
                                            phase_status={},
                                            metadata={"workflow_output_unwrapped": True},
                                        )
                            yield event
            except TimeoutError:
                duration = time.time() - workflow_start_time
                logger.error(
                    f"[Workflow {workflow_id}] TIMEOUT after {duration:.2f}s for task: {task_for_metadata[:50]}"
                )

                # Notify middlewares of timeout
                if hasattr(self.context, "middlewares"):
                    for mw in self.context.middlewares:
                        try:
                            await mw.on_end(
                                task_for_metadata,
                                {
                                    "workflowId": workflow_id,
                                    "mode": current_mode,
                                    "reasoning_effort": reasoning_effort,
                                    "end_time": datetime.now().isoformat(),
                                    "status": "FAILED",
                                    "error": "Workflow timed out",
                                },
                            )
                        except Exception as mw_error:
                            logger.warning(
                                f"Middleware.on_end() failed during timeout handling: {mw_error}"
                            )

                yield WorkflowStatusEvent(
                    state=WorkflowRunState.FAILED,
                    data={"message": "Workflow timed out", "workflow_id": workflow_id},
                )
                # Cleanup and exit early - do not emit fallback output after timeout
                self._cleanup_reasoning_effort_tracking(workflow_id)
                return
            except Exception as e:
                duration = time.time() - workflow_start_time
                logger.exception(
                    f"[Workflow {workflow_id}] ERROR after {duration:.2f}s for task: {task_for_metadata[:50]}: {e}"
                )

                # Notify middlewares of error
                if hasattr(self.context, "middlewares"):
                    for mw in self.context.middlewares:
                        try:
                            await mw.on_end(
                                task_for_metadata,
                                {
                                    "workflowId": workflow_id,
                                    "mode": current_mode,
                                    "reasoning_effort": reasoning_effort,
                                    "end_time": datetime.now().isoformat(),
                                    "status": "FAILED",
                                    "error": str(e),
                                },
                            )
                        except Exception as mw_error:
                            logger.warning(
                                f"Middleware.on_end() failed during exception handling: {mw_error}"
                            )

                yield WorkflowStatusEvent(
                    state=WorkflowRunState.FAILED,
                    data={"message": f"Workflow error: {e!s}", "workflow_id": workflow_id},
                )
                # Cleanup and exit early - do not emit fallback output after exception
                self._cleanup_reasoning_effort_tracking(workflow_id)
                return

            if final_msg is None and not saw_output_event:
                final_msg = await self._create_fallback_result(task_for_metadata)
                yield WorkflowOutputEvent(
                    data=self._create_output_event_data(final_msg), source_executor_id="fallback"
                )

            if final_msg is not None:
                final_dict = self._final_message_to_dict(final_msg)
                self.current_execution.update(
                    {
                        "result": final_dict.get("result"),
                        "routing": final_dict.get("routing"),
                        "quality": final_dict.get("quality"),
                        "execution_summary": final_dict.get("execution_summary", {}),
                        "phase_timings": final_dict.get("phase_timings", {}),
                        "phase_status": final_dict.get("phase_status", {}),
                        "metadata": final_dict.get("metadata", {}),
                    }
                )

                # Background evaluation for streaming runs (skip on resume).
                try:
                    score_value = float(final_dict.get("quality", {}).get("score", 0.0) or 0.0)
                except Exception:
                    score_value = 0.0
                if (
                    schedule_quality_eval
                    and not is_resume
                    and score_value <= 0.0
                    and str(final_dict.get("result") or "").strip()
                ):
                    self.current_execution.setdefault("quality", {})["pending"] = True
                    should_schedule_quality_eval = True

            self.current_execution["end_time"] = datetime.now().isoformat()

            # Log completion timing
            duration = time.time() - workflow_start_time
            logger.info(
                f"[Workflow {workflow_id}] Completed in {duration:.2f}s (mode={current_mode})"
            )

            if hasattr(self.context, "middlewares"):
                for mw in self.context.middlewares:
                    await mw.on_end(self.current_execution)

            if should_schedule_quality_eval and final_msg is not None:
                try:
                    from agentic_fleet.services.background_evaluation import (
                        schedule_quality_evaluation,
                    )

                    schedule_quality_evaluation(
                        workflow_id=workflow_id,
                        task=task_text,
                        answer=str(getattr(final_msg, "result", "") or ""),
                        history_manager=self.history_manager,
                    )
                except Exception:
                    pass

            # Cleanup reasoning effort tracking to prevent stale entries
            self._cleanup_reasoning_effort_tracking(workflow_id)

    async def _yield_fast_path_events(self, task: str) -> AsyncIterator[WorkflowEvent]:
        # Assertion for type checker - _should_fast_path ensures dspy_reasoner is not None
        assert self.dspy_reasoner is not None

        logger.info(f"Fast Path triggered for task: {task[:50]}...")
        # Skip generic status events for fast_path - they add no value to the UI
        # Only yield the actual response
        result_text = self.dspy_reasoner.generate_simple_response(task)

        execution_mode = self._map_mode_to_execution_mode(self.mode)
        final_msg = FinalResultMessage(
            result=result_text,
            routing=RoutingDecision(
                task=task,
                assigned_to=("FastResponder",),
                mode=execution_mode,
                subtasks=(task,),
            ),
            quality=QualityReport(score=10.0),
            judge_evaluations=[],
            execution_summary={},
            phase_timings={},
            phase_status={},
            metadata={"fast_path": True},
        )
        yield WorkflowOutputEvent(
            data=self._create_output_event_data(final_msg), source_executor_id="fastpath"
        )

    def _create_output_event_data(self, final_msg: FinalResultMessage) -> list[ChatMessage]:
        """Create output event data in list[ChatMessage] format."""
        # Convert structured data to dict
        data_dict = self._final_message_to_dict(final_msg)

        # Create ChatMessage with result text and metadata
        msg = ChatMessage(
            role=Role.ASSISTANT,
            text=final_msg.result,
            additional_properties=data_dict,
        )
        return [msg]

    def _final_message_to_dict(self, final_msg: FinalResultMessage) -> dict[str, Any]:
        pending = False
        try:
            pending = float(final_msg.quality.score or 0.0) <= 0.0 and not bool(
                final_msg.quality.used_fallback
            )
        except Exception:
            pending = False
        return {
            "result": final_msg.result,
            "routing": final_msg.routing.to_dict(),
            "quality": {
                "score": final_msg.quality.score,
                "missing": final_msg.quality.missing,
                "improvements": final_msg.quality.improvements,
                "judge_score": final_msg.quality.judge_score,
                "final_evaluation": final_msg.quality.final_evaluation,
                "used_fallback": final_msg.quality.used_fallback,
                "pending": pending,
            },
            "judge_evaluations": final_msg.judge_evaluations,
            "execution_summary": final_msg.execution_summary,
            "phase_timings": final_msg.phase_timings,
            "phase_status": final_msg.phase_status,
            "metadata": getattr(final_msg, "metadata", {}),
        }

    def _dict_to_final_message(self, data: dict[str, Any]) -> FinalResultMessage:
        return FinalResultMessage(
            result=data.get("result", ""),
            routing=ensure_routing_decision(data.get("routing", {})),
            quality=QualityReport(score=data.get("quality", {}).get("score", 0.0)),
            judge_evaluations=data.get("judge_evaluations", []),
            execution_summary=data.get("execution_summary", {}),
            phase_timings=data.get("phase_timings", {}),
            phase_status=data.get("phase_status", {}),
            metadata=data.get("metadata", {}),
        )

    async def _create_fallback_result(self, task: str) -> FinalResultMessage:
        execution_mode = self._map_mode_to_execution_mode(self.mode)
        return FinalResultMessage(
            result="Workflow execution completed (fallback)",
            routing=RoutingDecision(
                task=task,
                assigned_to=(),
                mode=execution_mode,
                subtasks=(),
            ),
            quality=QualityReport(score=0.0, used_fallback=True),
            judge_evaluations=[],
            execution_summary={},
            phase_timings={},
            phase_status={},
            metadata={"fallback": True},
        )


async def create_supervisor_workflow(
    *,
    compile_dspy: bool = True,
    config: WorkflowConfig | None = None,
    mode: str = "standard",
    context: SupervisorContext | None = None,
    dspy_routing_module: Any | None = None,
    dspy_quality_module: Any | None = None,
    dspy_tool_planning_module: Any | None = None,
) -> SupervisorWorkflow:
    """Create and initialize the supervisor workflow.

    Args:
        compile_dspy: Whether to compile DSPy modules
        config: Workflow configuration
        mode: Workflow mode (standard, handoff, group_chat, etc.)
        context: Pre-initialized context (optional)
        dspy_routing_module: Preloaded routing decision module (Phase 2)
        dspy_quality_module: Preloaded quality assessment module (Phase 2)
        dspy_tool_planning_module: Preloaded tool planning module (Phase 2)

    Returns:
        Initialized SupervisorWorkflow instance
    """
    if context is None:
        context = await initialize_workflow_context(config=config, compile_dspy=compile_dspy)

    # Phase 2: Attach decision modules to context if provided
    if dspy_routing_module is not None:
        context.dspy_routing_module = dspy_routing_module
    if dspy_quality_module is not None:
        context.dspy_quality_module = dspy_quality_module
    if dspy_tool_planning_module is not None:
        context.dspy_tool_planning_module = dspy_tool_planning_module

    if context.dspy_supervisor is None:
        raise RuntimeError("DSPy reasoner not initialized in context")

    # Phase 2: Inject preloaded decision modules into DSPy reasoner
    # This allows the reasoner to use compiled modules loaded at startup
    if (
        context.dspy_routing_module is not None
        or context.dspy_quality_module is not None
        or context.dspy_tool_planning_module is not None
    ):
        context.dspy_supervisor.set_decision_modules(
            routing_module=context.dspy_routing_module,
            quality_module=context.dspy_quality_module,
            tool_planning_module=context.dspy_tool_planning_module,
        )
        logger.info("Injected preloaded decision modules into DSPy reasoner")

    # Build workflow
    workflow_builder = build_fleet_workflow(
        context.dspy_supervisor,
        context,
        mode=mode,  # type: ignore[arg-type]
    )
    workflow = _materialize_workflow(workflow_builder)

    return SupervisorWorkflow(context, workflow, mode=mode)
