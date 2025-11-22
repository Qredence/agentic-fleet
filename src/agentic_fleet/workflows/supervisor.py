"""Supervisor workflow entrypoints.

Consolidated public API and implementation.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from agent_framework import (
    AgentRunUpdateEvent,
    ChatMessage,
    ExecutorCompletedEvent,
    MagenticAgentMessageEvent,
    RequestInfoEvent,
    Role,
    WorkflowOutputEvent,
    WorkflowRunState,
    WorkflowStartedEvent,
    WorkflowStatusEvent,
)

if TYPE_CHECKING:
    from agent_framework import Workflow

from ..utils.history_manager import HistoryManager
from ..utils.logger import setup_logger
from ..utils.models import ExecutionMode, RoutingDecision, ensure_routing_decision
from ..utils.tool_registry import ToolRegistry
from .builder import build_fleet_workflow
from .config import WorkflowConfig
from .context import SupervisorContext
from .handoff import HandoffManager
from .initialization import initialize_workflow_context
from .messages import FinalResultMessage, TaskMessage
from .models import QualityReport

logger = setup_logger(__name__)


class SupervisorWorkflow:
    """Workflow that drives the AgenticFleet orchestration pipeline."""

    def __init__(
        self,
        context: SupervisorContext,
        workflow_runner: Workflow | None = None,
        dspy_supervisor: Any | None = None,
        *,
        agents: dict[str, Any] | None = None,
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

    def _is_simple_task(self, task: str) -> bool:
        import re

        task_lower = task.strip().lower()

        # Keywords that imply real-time or specific entity knowledge
        complex_keywords = [
            "news",
            "latest",
            "current",
            "election",
            "price",
            "stock",
            "weather",
            "who is",
            "who won",
            "who are",
            "mayor",
            "governor",
            "president",
        ]

        # Heartbeat / greeting style tasks that should be answered directly
        trivial_keywords = [
            "ping",
            "hello",
            "hi",
            "hey",
            "test",
            "are you there",
            "you there",
            "you awake",
        ]

        # Keywords that imply a simple deterministic response
        simple_keywords = ["define", "calculate", "solve", "2+", "meaning of"]

        is_time_sensitive = bool(re.search(r"20[2-9][0-9]", task))
        has_complex_keyword = any(k in task_lower for k in complex_keywords)
        has_trivial_keyword = any(k in task_lower for k in trivial_keywords)
        has_simple_keyword = any(k in task_lower for k in simple_keywords)

        # Consider very short, punctuation-free tasks as simple if not time-sensitive
        if is_time_sensitive or has_complex_keyword:
            return False

        return has_trivial_keyword or has_simple_keyword

    async def run(self, task: str) -> dict[str, Any]:
        start_time = datetime.now()
        workflow_id = str(uuid4())

        if (
            self.mode == "auto"
            and self.dspy_reasoner
            and hasattr(self.dspy_reasoner, "select_workflow_mode")
        ):
            logger.info(f"Auto-detecting workflow mode for task: {task[:50]}...")
            decision = self.dspy_reasoner.select_workflow_mode(task)
            detected_mode = decision.get("mode", "standard")

            # Map 'fast_path' to internal handling
            if detected_mode == "fast_path":
                logger.info(f"Fast Path triggered for task: {task[:50]}...")
                result_text = self.dspy_reasoner.generate_simple_response(task)
                execution_record = {
                    "workflowId": workflow_id,
                    "task": task,
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "result": result_text,
                    "routing": RoutingDecision(
                        task=task,
                        assigned_to=("FastResponder",),
                        mode=ExecutionMode.DELEGATED,
                        subtasks=(task,),
                    ).to_dict(),
                    "quality": {"score": 10.0},
                    "metadata": {"fast_path": True, "mode_reasoning": decision.get("reasoning")},
                }
                if self.history_manager:
                    try:
                        await self.history_manager.save_execution_async(execution_record)
                    except Exception:
                        logger.debug("Failed to persist fast-path execution history", exc_info=True)
                return {
                    "result": result_text,
                    "routing": RoutingDecision(
                        task=task,
                        assigned_to=("FastResponder",),
                        mode=ExecutionMode.DELEGATED,
                        subtasks=(task,),
                    ).to_dict(),
                    "quality": {"score": 10.0},
                    "judge_evaluations": [],
                    "execution_summary": {},
                    "phase_timings": {},
                    "phase_status": {},
                    "metadata": {"fast_path": True, "mode_reasoning": decision.get("reasoning")},
                }

            # If not fast path, update mode and rebuild workflow if necessary
            # Note: Changing mode at runtime requires rebuilding the workflow graph.
            # The current architecture builds the graph at initialization.
            # Ideally, we should select mode *before* creating the SupervisorWorkflow,
            # or SupervisorWorkflow should support dynamic dispatch.
            # Given the current structure, we will log and potentially warn if mode switch is needed but not supported dynamically yet,
            # OR we can support dynamic dispatch if we have access to the builder.

            # For now, we'll only support dynamic dispatch if the current mode allows or if we re-initialize.
            # Actually, create_supervisor_workflow is the factory.
            # But since we are already IN run(), the workflow object is already built.
            # HACK: If the detected mode differs from the initialized mode (likely 'standard' fallback),
            # and we are in 'auto', we might be stuck.
            # However, since we haven't fully implemented dynamic graph rebuilding in run(),
            # we will proceed with the initialized workflow unless it's fast_path (handled above).
            # To truly support auto-mode, the runner should call select_workflow_mode BEFORE instantiating SupervisorWorkflow.
            # Note: Dynamic graph switching not yet implemented in run(); handled in CLI runner layer.

        if self.dspy_reasoner and self._is_simple_task(task):
            logger.info(f"Fast Path triggered for task: {task[:50]}...")
            result_text = self.dspy_reasoner.generate_simple_response(task)
            execution_record = {
                "workflowId": workflow_id,
                "task": task,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "result": result_text,
                "routing": RoutingDecision(
                    task=task,
                    assigned_to=("FastResponder",),
                    mode=ExecutionMode.DELEGATED,
                    subtasks=(task,),
                ).to_dict(),
                "quality": {"score": 10.0},
                "metadata": {"fast_path": True},
            }
            if self.history_manager:
                try:
                    await self.history_manager.save_execution_async(execution_record)
                except Exception:
                    logger.debug("Failed to persist fast-path execution history", exc_info=True)
            return {
                "result": result_text,
                "routing": RoutingDecision(
                    task=task,
                    assigned_to=("FastResponder",),
                    mode=ExecutionMode.DELEGATED,
                    subtasks=(task,),
                ).to_dict(),
                "quality": {"score": 10.0},
                "judge_evaluations": [],
                "execution_summary": {},
                "phase_timings": {},
                "phase_status": {},
                "metadata": {"fast_path": True},
            }

        if self.workflow is None:
            raise RuntimeError("Workflow runner not initialized.")

        self.current_execution = {
            "workflowId": workflow_id,
            "task": task,
            "start_time": start_time.isoformat(),
            "mode": self.mode,
        }

        logger.info(f"Running fleet workflow for task: {task[:50]}...")

        if self.mode in ("group_chat", "handoff"):
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

            return {
                "result": result_text,
                "routing": {"mode": self.mode},
                "quality": {"score": 0.0},
                "judge_evaluations": [],
                "metadata": {"mode": self.mode},
            }

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

        if self.history_manager:
            try:
                await self.history_manager.save_execution_async(self.current_execution)
            except Exception:
                logger.debug("Failed to persist execution history", exc_info=True)

        return result_dict

    async def run_stream(self, task: str):
        logger.info(f"Running fleet workflow (streaming) for task: {task[:50]}...")
        workflow_id = str(uuid4())

        if self.dspy_reasoner and self._is_simple_task(task):
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
                data=self._final_message_to_dict(final_msg), source_executor_id="fastpath"
            )
            yield WorkflowStatusEvent(state=WorkflowRunState.IDLE, data=None)
            return

        if self.workflow is None:
            raise RuntimeError("Workflow runner not initialized.")

        self.current_execution = {
            "workflowId": workflow_id,
            "task": task,
            "start_time": datetime.now().isoformat(),
        }

        final_msg = None
        if self.mode in ("group_chat", "handoff"):
            msg = ChatMessage(role=Role.USER, text=task)
            async for event in self.workflow.run_stream(msg):
                if isinstance(event, MagenticAgentMessageEvent):
                    yield event
                elif isinstance(event, AgentRunUpdateEvent):
                    # Convert AgentRunUpdateEvent to MagenticAgentMessageEvent for CLI compatibility
                    text = ""
                    if hasattr(event, "run") and hasattr(event.run, "delta"):
                        delta = event.run.delta
                        if hasattr(delta, "content") and delta.content:
                            # Handle list of content parts or string
                            if isinstance(delta.content, list):
                                text = "".join(str(part) for part in delta.content)
                            else:
                                text = str(delta.content)

                    if text:
                        # Create synthetic event for CLI streaming
                        mag_msg = ChatMessage(role=Role.ASSISTANT, text=text)
                        agent_id = (
                            getattr(event.run, "agent_id", "unknown")
                            if hasattr(event, "run")
                            else "unknown"
                        )
                        mag_event = MagenticAgentMessageEvent(agent_id=agent_id, message=mag_msg)
                        yield mag_event

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
                            assigned_to=(self.mode,),
                            mode=ExecutionMode.DELEGATED,  # or GroupChat/Handoff specific
                            subtasks=(task,),
                        ),
                        quality=QualityReport(score=0.0),
                        judge_evaluations=[],
                        execution_summary={},
                        phase_timings={},
                        phase_status={},
                        metadata={"mode": self.mode},
                    )
                    # Yield the formatted output event
                    yield WorkflowOutputEvent(
                        data=self._final_message_to_dict(final_msg),
                        source_executor_id=self.mode,
                    )
        else:
            task_msg = TaskMessage(task=task)
            async for event in self.workflow.run_stream(task_msg):
                if isinstance(event, MagenticAgentMessageEvent | ExecutorCompletedEvent):
                    yield event
                elif isinstance(event, WorkflowOutputEvent):
                    if hasattr(event, "data"):
                        data = event.data
                        if isinstance(data, FinalResultMessage):
                            final_msg = data
                            # Convert to dict for consistency with run() and CLI expectations
                            dict_data = self._final_message_to_dict(data)
                            yield WorkflowOutputEvent(
                                data=dict_data,
                                source_executor_id=getattr(event, "source_executor_id", "workflow"),
                            )
                            continue
                        elif isinstance(data, dict) and "result" in data:
                            final_msg = self._dict_to_final_message(data)
                    yield event

        if final_msg is None and self.mode not in ("group_chat", "handoff"):
            final_msg = await self._create_fallback_result(task)
            yield WorkflowOutputEvent(
                data=self._final_message_to_dict(final_msg), source_executor_id="fallback"
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
        if self.history_manager:
            await self.history_manager.save_execution_async(self.current_execution)

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
    workflow = workflow_builder.build()

    return SupervisorWorkflow(context, workflow, mode=mode)
