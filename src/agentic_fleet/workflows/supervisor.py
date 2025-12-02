"""Supervisor workflow entrypoints.

Consolidated public API and implementation.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import (
    AgentRunUpdateEvent,
    ExecutorCompletedEvent,
    MagenticAgentMessageEvent,
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
from .builder import build_fleet_workflow
from .config import WorkflowConfig
from .context import SupervisorContext
from .execution.streaming_events import ReasoningStreamEvent
from .handoff import HandoffManager
from .helpers import is_simple_task
from .initialization import initialize_workflow_context
from .messages import FinalResultMessage, TaskMessage
from .models import QualityReport

if TYPE_CHECKING:
    from agent_framework._agents import ChatAgent
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
)

logger = setup_logger(__name__)


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

    def _get_mode_decision(self, task: str) -> dict[str, str]:
        """Get cached mode decision for a task.

        Caches the result to avoid duplicate DSPy calls within the same workflow run.

        Args:
            task: The task string to evaluate

        Returns:
            Dictionary with 'mode' and 'reasoning' keys
        """
        # Check if we have a cached decision for this task
        cache_key = f"mode_decision_{hash(task)}"
        cached = getattr(self, "_mode_decision_cache", {}).get(cache_key)
        if cached is not None:
            return cached

        # Initialize cache if needed
        if not hasattr(self, "_mode_decision_cache"):
            self._mode_decision_cache: dict[str, dict[str, str]] = {}

        # Compute mode decision
        if (
            self.mode == "auto"
            and self.dspy_reasoner
            and hasattr(self.dspy_reasoner, "select_workflow_mode")
        ):
            decision = self.dspy_reasoner.select_workflow_mode(task)
        else:
            decision = {"mode": self.mode, "reasoning": ""}

        # Cache and return
        self._mode_decision_cache[cache_key] = decision
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

        # Check auto-mode fast-path detection (uses cached decision)
        if self.mode == "auto":
            decision = self._get_mode_decision(task)
            if decision.get("mode") == "fast_path":
                return True

        # Check simple task heuristic
        return is_simple_task(task)

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
            mode=ExecutionMode.DELEGATED,
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

    async def run(self, task: str) -> dict[str, Any]:
        """Execute the workflow for a single task."""
        with optional_span("SupervisorWorkflow.run", attributes={"task": task, "mode": self.mode}):
            start_time = datetime.now()
            workflow_id = str(uuid4())
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
                result = await self.workflow.run(msg)

                # Handle Handoff/GroupChat result (usually a list of messages or a single message)
                result_text = ""
                if isinstance(result, list):  # List[ChatMessage]
                    # Find the last message
                    if result:
                        last_msg = result[-1]
                        result_text = last_msg.text
                elif hasattr(result, "content"):
                    result_text = str(result.content)
                else:
                    result_text = str(result)

                # Persist execution history
                self.current_execution.update(
                    {
                        "result": result_text,
                        "routing": {"mode": current_mode},
                        "quality": {"score": 0.0},
                        "end_time": datetime.now().isoformat(),
                    }
                )
                result_dict = {
                    "result": result_text,
                    "routing": {"mode": current_mode},
                    "quality": {"score": 0.0},
                    "judge_evaluations": [],
                    "metadata": {"mode": current_mode},
                }
                if hasattr(self.context, "middlewares"):
                    for mw in self.context.middlewares:
                        await mw.on_end(result_dict)
                return result_dict

            task_msg = TaskMessage(task=task)
            result = await self.workflow.run(task_msg)
            outputs = result.get_outputs() if hasattr(result, "get_outputs") else []
            if not outputs:
                raise RuntimeError("Workflow did not produce any outputs")

            final_msg = outputs[-1]
            if not isinstance(final_msg, FinalResultMessage):
                # Fallback if final message type mismatch (should not happen in standard flow)
                return {"result": str(final_msg)}

            result_dict = self._final_message_to_dict(final_msg)

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

            return result_dict

    def _handle_agent_run_update(
        self, event: AgentRunUpdateEvent
    ) -> ReasoningStreamEvent | MagenticAgentMessageEvent | None:
        """Handle AgentRunUpdateEvent and convert to appropriate stream event.

        Extracts reasoning tokens (GPT-5 models) or converts to MagenticAgentMessageEvent
        for CLI compatibility.

        Args:
            event: The AgentRunUpdateEvent to process

        Returns:
            ReasoningStreamEvent, MagenticAgentMessageEvent, or None if no content
        """
        if not (hasattr(event, "run") and hasattr(event.run, "delta")):
            return None

        delta = event.run.delta

        # Check for reasoning content (GPT-5 series)
        if hasattr(delta, "type") and "reasoning" in str(getattr(delta, "type", "")):
            reasoning_text = getattr(delta, "delta", "")
            if reasoning_text:
                agent_id = getattr(event.run, "agent_id", "unknown")
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
            agent_id = getattr(event.run, "agent_id", "unknown")
            mag_msg = ChatMessage(role=Role.ASSISTANT, text=text)
            return MagenticAgentMessageEvent(agent_id=agent_id, message=mag_msg)

        return None

    def _apply_reasoning_effort(self, reasoning_effort: str | None) -> None:
        """Apply reasoning effort to all agents that support it.

        Note: This method mutates shared agent state. When multiple concurrent
        requests have different reasoning_effort values, they may overwrite each
        other's settings. For production use with concurrent requests, consider
        implementing request-scoped agent instances or passing reasoning_effort
        through the workflow context instead of mutating shared state.

        Args:
            reasoning_effort: Reasoning effort level ("minimal", "medium", "maximal").
                Must match API schema values defined in ChatRequest.
        """
        if not self.agents:
            return

        for agent_name, agent in self.agents.items():
            if hasattr(agent, "chat_client"):
                chat_client = agent.chat_client
                try:
                    # Try setting via extra_body (most common approach)
                    # Type ignores needed for dynamic attribute assignment on chat clients
                    if hasattr(chat_client, "extra_body"):
                        existing = dict(getattr(chat_client, "extra_body", None) or {})
                        existing["reasoning"] = {"effort": reasoning_effort}
                        chat_client.extra_body = existing  # type: ignore[assignment]
                    elif hasattr(chat_client, "_default_extra_body"):
                        existing = dict(getattr(chat_client, "_default_extra_body", None) or {})
                        existing["reasoning"] = {"effort": reasoning_effort}
                        chat_client._default_extra_body = existing  # type: ignore[assignment]
                    else:
                        # Store as attribute for later use
                        chat_client._reasoning_effort = reasoning_effort  # type: ignore[assignment]
                    logger.debug(
                        f"Applied reasoning_effort={reasoning_effort} to agent {agent_name}"
                    )
                except AttributeError as e:
                    logger.warning(
                        f"Agent {agent_name} chat_client doesn't support reasoning_effort: {e}"
                    )
                except TypeError as e:
                    logger.warning(
                        f"Invalid type when setting reasoning_effort on {agent_name}: {e}"
                    )
                except Exception as e:
                    logger.error(
                        f"Unexpected error setting reasoning_effort on {agent_name}: {e}",
                        exc_info=True,
                    )

    async def run_stream(
        self,
        task: str,
        *,
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[WorkflowEvent]:
        """Execute the workflow for a single task, streaming events.

        Args:
            task: The task string to execute
            reasoning_effort: Optional reasoning effort override (minimal, medium, maximal)

        Yields:
            WorkflowEvent: Workflow events including status updates, agent messages,
                and the final output event containing the result.
        """
        with optional_span(
            "SupervisorWorkflow.run_stream", attributes={"task": task, "mode": self.mode}
        ):
            logger.info(f"Running fleet workflow (streaming) for task: {task[:50]}...")
            workflow_id = str(uuid4())
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
                                task,
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
                self._apply_reasoning_effort(reasoning_effort)

            # Notify middlewares
            if hasattr(self.context, "middlewares"):
                for mw in self.context.middlewares:
                    await mw.on_start(
                        task,
                        {
                            "workflowId": workflow_id,
                            "mode": current_mode,
                            "reasoning_effort": reasoning_effort,
                            "start_time": datetime.now().isoformat(),
                        },
                    )

            # Unified fast-path check for streaming
            if self._should_fast_path(task):
                async for event in self._yield_fast_path_events(task):
                    yield event
                return

            if self.workflow is None:
                raise RuntimeError("Workflow runner not initialized.")

            self.current_execution = {
                "workflowId": workflow_id,
                "task": task,
                "start_time": datetime.now().isoformat(),
            }

            final_msg = None
            if current_mode in ("group_chat", "handoff"):
                msg = ChatMessage(role=Role.USER, text=task)
                async for event in self.workflow.run_stream(msg):
                    if isinstance(event, MagenticAgentMessageEvent):
                        yield event
                    elif isinstance(event, AgentRunUpdateEvent):
                        converted = self._handle_agent_run_update(event)
                        if converted is not None:
                            yield converted
                            if isinstance(converted, ReasoningStreamEvent):
                                continue

                    elif isinstance(event, RequestInfoEvent):
                        # If request contains conversation, extracting last message might be useful
                        if hasattr(event.data, "conversation") and event.data.conversation:
                            last_msg = event.data.conversation[-1]
                            # Log or capture partial result
                            logger.info(
                                f"RequestInfoEvent: Last message from {last_msg.author_name}: {last_msg.text[:50]}..."
                            )

                    elif isinstance(event, WorkflowOutputEvent) and (
                        isinstance(event.data, list)
                        and event.data
                        and isinstance(event.data[0], ChatMessage)
                    ):
                        last_msg = event.data[-1]
                        final_msg = FinalResultMessage(
                            result=last_msg.text,
                            routing=RoutingDecision(
                                task=task,
                                assigned_to=(current_mode,),
                                mode=ExecutionMode.DELEGATED,  # or GroupChat/Handoff specific
                                subtasks=(task,),
                            ),
                            quality=QualityReport(score=0.0),
                            judge_evaluations=[],
                            execution_summary={},
                            phase_timings={},
                            phase_status={},
                            metadata={"mode": current_mode},
                        )
                        # Yield the formatted output event
                        yield WorkflowOutputEvent(
                            data=self._create_output_event_data(final_msg),
                            source_executor_id=current_mode,
                        )
            else:
                task_msg = TaskMessage(task=task)
                async for event in self.workflow.run_stream(task_msg):
                    if isinstance(event, MagenticAgentMessageEvent | ExecutorCompletedEvent):
                        yield event
                    elif isinstance(event, AgentRunUpdateEvent):
                        converted = self._handle_agent_run_update(event)
                        if converted is not None:
                            yield converted
                            if isinstance(converted, ReasoningStreamEvent):
                                continue
                    elif isinstance(event, WorkflowOutputEvent):
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
                            elif isinstance(data, list) and data:
                                # Handle legacy list[ChatMessage] format from strategies
                                last_msg = data[-1]
                                text = getattr(last_msg, "text", str(last_msg))
                                final_msg = FinalResultMessage(
                                    result=text,
                                    routing=RoutingDecision(
                                        task=task,
                                        assigned_to=(),
                                        mode=ExecutionMode.SEQUENTIAL,
                                        subtasks=(),
                                    ),
                                    quality=QualityReport(score=0.0),
                                    judge_evaluations=[],
                                    execution_summary={},
                                    phase_timings={},
                                    phase_status={},
                                    metadata={"legacy_list_output": True},
                                )
                        yield event

            if final_msg is None and current_mode not in ("group_chat", "handoff"):
                final_msg = await self._create_fallback_result(task)
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

            self.current_execution["end_time"] = datetime.now().isoformat()
            if hasattr(self.context, "middlewares"):
                for mw in self.context.middlewares:
                    await mw.on_end(self.current_execution)

    async def _yield_fast_path_events(self, task: str) -> AsyncIterator[WorkflowEvent]:
        # Assertion for type checker - _should_fast_path ensures dspy_reasoner is not None
        assert self.dspy_reasoner is not None

        logger.info(f"Fast Path triggered for task: {task[:50]}...")
        yield WorkflowStartedEvent(data=None)
        yield WorkflowStatusEvent(state=WorkflowRunState.IN_PROGRESS, data=None)
        result_text = self.dspy_reasoner.generate_simple_response(task)

        final_msg = FinalResultMessage(
            result=result_text,
            routing=RoutingDecision(
                task=task,
                assigned_to=("FastResponder",),
                mode=ExecutionMode.DELEGATED,
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
        yield WorkflowStatusEvent(state=WorkflowRunState.IDLE, data=None)

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
        return {
            "result": final_msg.result,
            "routing": final_msg.routing.to_dict(),
            "quality": {"score": final_msg.quality.score, "missing": final_msg.quality.missing},
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
        return FinalResultMessage(
            result="Workflow execution completed (fallback)",
            routing=RoutingDecision(
                task=task,
                assigned_to=(),
                mode=ExecutionMode.DELEGATED,
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
) -> SupervisorWorkflow:
    """Create and initialize the supervisor workflow."""
    if context is None:
        context = await initialize_workflow_context(config=config, compile_dspy=compile_dspy)

    if context.dspy_supervisor is None:
        raise RuntimeError("DSPy reasoner not initialized in context")

    # Build workflow
    workflow_builder = build_fleet_workflow(
        context.dspy_supervisor,
        context,
        mode=mode,  # type: ignore[arg-type]
    )
    workflow = _materialize_workflow(workflow_builder)

    return SupervisorWorkflow(context, workflow, mode=mode)
