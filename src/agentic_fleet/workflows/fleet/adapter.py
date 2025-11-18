"""Supervisor workflow implementation backed by agent-framework WorkflowBuilder.

This adapter is the canonical implementation used by the CLI and application
code.  It also provides a set of backward-compatibility shims so that legacy
tests which exercised the old, DSPy-centric ``SupervisorWorkflow`` API
continue to pass while the runtime migrates to the fleet workflow design.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from agent_framework import ChatMessage, MagenticAgentMessageEvent, Role, WorkflowOutputEvent

if TYPE_CHECKING:
    # Workflow is only needed for type checking; runtime uses Protocol methods.
    from agent_framework import Workflow

from ...agents import create_workflow_agents
from ...utils.agent_framework_shims import ensure_agent_framework_shims
from ...utils.cache import TTLCache
from ...utils.env import validate_agentic_fleet_env
from ...utils.history_manager import HistoryManager
from ...utils.logger import setup_logger
from ...utils.models import ExecutionMode, RoutingDecision, ensure_routing_decision
from ...utils.tool_registry import ToolRegistry
from ..config import WorkflowConfig
from ..execution import (
    execute_delegated_streaming,
    execute_parallel,
    execute_parallel_streaming,
    execute_sequential_streaming,
)
from ..execution.sequential import format_handoff_input
from ..execution.streaming_events import create_system_event
from ..handoff_manager import HandoffManager
from ..orchestration import SupervisorContext
from ..shared.models import QualityReport
from ..shared.quality import quality_report_to_legacy
from ..utils import (
    derive_objectives,
    estimate_remaining_work,
    extract_artifacts,
    synthesize_results,
)
from .builder import build_fleet_workflow
from .messages import FinalResultMessage, TaskMessage

logger = setup_logger(__name__)


class SupervisorWorkflow:
    """Workflow that drives the AgenticFleet orchestration pipeline."""

    def __init__(
        self,
        context: SupervisorContext | WorkflowConfig | None = None,
        workflow_runner: Workflow | None = None,
        dspy_supervisor: Any | None = None,
        *,
        agents: dict[str, Any] | None = None,
        history_manager: HistoryManager | None = None,
        tool_registry: ToolRegistry | None = None,
        handoff_manager: HandoffManager | None = None,
        **_: Any,
    ) -> None:
        """Initialize SupervisorWorkflow.

        The constructor intentionally accepts both the new ``SupervisorContext``
        (preferred) and the legacy ``WorkflowConfig`` used in older tests.  When
        a context is provided, the instance runs in *fleet mode* and delegates
        to an agent-framework workflow agent.  When only a config/agents/
        supervisor are provided, the instance operates in *legacy mode* using
        direct DSPy orchestration for backward compatibility.
        """

        # Detect whether we're running with a full SupervisorContext (fleet
        # mode) or a bare WorkflowConfig/None (legacy mode used in tests).
        self.context: SupervisorContext | None = None
        self.config: WorkflowConfig | None = None

        if isinstance(context, SupervisorContext):
            self.context = context
            self.config = context.config
            self.workflow = workflow_runner
        else:
            # ``context`` may actually be a WorkflowConfig from older tests.
            if isinstance(context, WorkflowConfig):
                self.config = context
            elif isinstance(workflow_runner, WorkflowConfig) and context is None:
                # Some tests pass (None, WorkflowConfig(...)).
                self.config = workflow_runner
                workflow_runner = None

            self.context = None
            self.workflow = workflow_runner

        # Allow explicit override for tests that pass dspy_supervisor; fall
        # back to context supervisor when available.
        self.dspy_supervisor = dspy_supervisor or (
            getattr(self.context, "dspy_supervisor", None) if self.context else None
        )

        # Agents, tool registry, and managers come from explicit parameters
        # first, then fall back to context-provided instances.
        self.agents = agents or (getattr(self.context, "agents", None) if self.context else None)
        self.tool_registry: ToolRegistry | None = tool_registry or (
            getattr(self.context, "tool_registry", None) if self.context else None
        )
        self.handoff_manager: HandoffManager | None = handoff_manager or (
            getattr(self.context, "handoff_manager", None) if self.context else None
        )
        self.history_manager: HistoryManager | None = history_manager or (
            getattr(self.context, "history_manager", None) if self.context else None
        )

        # Default managers for bare/legacy construction paths so tests can
        # assign attributes without checking for None.
        if self.history_manager is None:
            self.history_manager = HistoryManager()
        if self.tool_registry is None:
            self.tool_registry = ToolRegistry()

        # Handoff toggle - default to config flag when available, otherwise
        # enabled for backward compatibility.
        self.enable_handoffs: bool = True
        if self.context is not None:
            self.enable_handoffs = bool(getattr(self.context, "enable_handoffs", True))
        elif self.config is not None:
            self.enable_handoffs = bool(getattr(self.config, "enable_handoffs", True))

        # Optional analysis cache (used primarily in fleet mode).
        self.analysis_cache: TTLCache[str, dict[str, Any]] | None = (
            getattr(self.context, "analysis_cache", None) if self.context else None
        )
        self.execution_history: list[dict[str, Any]] = []
        self.current_execution: dict[str, Any] = {}
        # Back-compat attributes referenced by some tests
        self._compilation_task = getattr(context, "compilation_task", None) if context else None
        self._compilation_status = (
            getattr(context, "compilation_status", "pending") if context else "pending"
        )
        self._compiled_supervisor = None

        # Ensure we always have a supervisor instance for legacy tests that
        # capture ``workflow.dspy_supervisor`` before initialization.
        if self.dspy_supervisor is None:
            from ...dspy_modules.supervisor import DSPySupervisor

            self.dspy_supervisor = DSPySupervisor(use_enhanced_signatures=True)

    async def run(self, task: str) -> dict[str, Any]:
        """Execute workflow for a task (non-streaming).

        Args:
            task: Task to execute

        Returns:
            Dictionary with result, routing, quality, etc.
        """
        # If a Workflow agent is available, delegate to the fleet workflow.
        if self.workflow is not None:
            logger.info(f"Running fleet workflow for task: {task[:100]}...")

            task_msg = TaskMessage(task=task)
            try:
                result = await self.workflow.run(task_msg)
            except Exception as e:  # pragma: no cover - fleet path exercised elsewhere
                logger.exception(f"Workflow execution failed: {e}")
                raise

            outputs = result.get_outputs() if hasattr(result, "get_outputs") else []
            if not outputs:
                raise RuntimeError("Workflow did not produce any outputs")

            final_msg = outputs[-1]
            if not isinstance(final_msg, FinalResultMessage):
                raise RuntimeError(f"Expected FinalResultMessage, got {type(final_msg)}")

            return self._final_message_to_dict(final_msg)

        # Legacy mode: run directly against DSPy supervisor and agents.
        return await self._run_legacy(task)

    async def run_stream(self, task: str):
        """Execute workflow with streaming events.

        Args:
            task: Task to execute

        Yields:
            MagenticAgentMessageEvent and WorkflowOutputEvent instances
        """
        # Fleet mode streaming path: delegate to the underlying workflow agent.
        if self.workflow is not None:
            logger.info(f"Running fleet workflow (streaming) for task: {task[:100]}...")

            execution_start = datetime.now()
            workflow_id = str(uuid4())
            self.current_execution = {
                "workflowId": workflow_id,
                "task": task,
                "start_time": execution_start.isoformat(),
                "events": [],
                "dspy_analysis": {},
                "routing": {},
                "progress": {},
                "agent_executions": [],
                "quality": {},
                "result": None,
                "phase_timings": {},
                "phase_status": {},
            }

            task_msg = TaskMessage(task=task)

            try:
                final_msg: FinalResultMessage | None = None

                async for event in self.workflow.run_stream(task_msg):
                    if isinstance(event, MagenticAgentMessageEvent):
                        yield event
                    elif isinstance(event, WorkflowOutputEvent):
                        if hasattr(event, "data"):
                            data = event.data
                            if isinstance(data, FinalResultMessage):
                                final_msg = data
                            elif isinstance(data, dict) and "result" in data:
                                final_msg = self._dict_to_final_message(data)
                        yield event
                    else:
                        yield MagenticAgentMessageEvent(
                            agent_id="fleet",
                            message=ChatMessage(
                                role=Role.ASSISTANT,
                                text=str(event),
                            ),
                        )

                if final_msg is None:
                    try:
                        result = await self.workflow.run(task_msg)
                        outputs = result.get_outputs() if hasattr(result, "get_outputs") else []
                        if outputs:
                            final_output = outputs[-1]
                            if isinstance(final_output, FinalResultMessage):
                                final_msg = final_output
                    except Exception as e:  # pragma: no cover - defensive
                        logger.warning(f"Could not get final result from workflow: {e}")

                if final_msg is None:
                    logger.warning("No final message found, creating fallback")
                    final_msg = await self._create_fallback_result(task)

                yield WorkflowOutputEvent(
                    data=self._final_message_to_dict(final_msg),
                    source_executor_id="fleet",
                )

                execution_end = datetime.now()
                execution_start_dt = datetime.fromisoformat(self.current_execution["start_time"])
                total_time = (execution_end - execution_start_dt).total_seconds()
                self.current_execution["end_time"] = execution_end.isoformat()
                self.current_execution["total_time_seconds"] = total_time

                self.execution_history.append(self.current_execution.copy())
                if self.history_manager:
                    await self.history_manager.save_execution_async(self.current_execution)

            except Exception as e:  # pragma: no cover - fleet path exercised elsewhere
                logger.exception(f"Workflow streaming failed: {e}")
                raise

            return

        # Legacy mode: emit structured streaming events produced by the
        # legacy DSPy pipeline for backward compatibility.
        async for event in self._legacy_execution_flow(task):
            yield event

    def _final_message_to_dict(self, final_msg: FinalResultMessage) -> dict[str, Any]:
        """Convert FinalResultMessage to dict format for backward compatibility."""
        # Convert quality report to dict
        quality_dict = quality_report_to_legacy(final_msg.quality)

        return {
            "result": final_msg.result,
            "routing": final_msg.routing.to_dict(),
            "quality": quality_dict,
            "judge_evaluations": final_msg.judge_evaluations,
            "execution_summary": final_msg.execution_summary,
            "phase_timings": final_msg.phase_timings,
            "phase_status": final_msg.phase_status,
        }

    def _dict_to_final_message(self, data: dict[str, Any]) -> FinalResultMessage:
        """Convert dict to FinalResultMessage."""
        from ..shared.quality import quality_report_from_legacy

        routing = ensure_routing_decision(data.get("routing", {}))
        quality = quality_report_from_legacy(data.get("quality", {}))

        return FinalResultMessage(
            result=data.get("result", ""),
            routing=routing,
            quality=quality,
            judge_evaluations=data.get("judge_evaluations", []),
            execution_summary=data.get("execution_summary", {}),
            phase_timings=data.get("phase_timings", {}),
            phase_status=data.get("phase_status", {}),
            metadata=data.get("metadata", {}),
        )

    async def _create_fallback_result(self, task: str) -> FinalResultMessage:
        """Create fallback result if workflow doesn't produce one."""
        from ...utils.models import ExecutionMode

        return FinalResultMessage(
            result="Workflow execution completed but no result was produced",
            routing=RoutingDecision(
                task=task,
                assigned_to=(),
                mode=ExecutionMode.DELEGATED,
                subtasks=(),
                tool_requirements=(),
                confidence=None,
            ),
            quality=QualityReport(score=0.0, used_fallback=True),
            judge_evaluations=[],
            execution_summary={},
            phase_timings={},
            phase_status={},
            metadata={"fallback": True},
        )

    # ------------------------------------------------------------------
    # Legacy orchestration path (used only when no Workflow agent exists)
    # ------------------------------------------------------------------
    async def _run_legacy(self, task: str) -> dict[str, Any]:
        """Execute the original DSPy-driven workflow logic."""

        final_payload: dict[str, Any] | None = None
        async for event in self._legacy_execution_flow(task):
            if isinstance(event, WorkflowOutputEvent):
                data = event.data
                if isinstance(data, dict):
                    final_payload = data

        if final_payload is None:
            raise RuntimeError("Legacy workflow did not produce a final result")

        return final_payload

    async def _legacy_execution_flow(self, task: str):
        """Async generator that runs the legacy pipeline with streaming events."""

        supervisor = self._require_supervisor()
        agents = self._require_agents()
        config = self.config or WorkflowConfig()

        execution_start = datetime.now()
        workflow_id = str(uuid4())

        self.current_execution = {
            "workflowId": workflow_id,
            "task": task,
            "start_time": execution_start.isoformat(),
            "events": [],
            "dspy_analysis": {},
            "routing": {},
            "progress": {},
            "agent_executions": [],
            "quality": {},
            "result": None,
            "phase_timings": {},
            "phase_status": {},
        }

        # --- Analysis ---------------------------------------------------------
        try:
            analysis = supervisor.analyze_task(task)
        except Exception:  # pragma: no cover - defensive
            analysis = {"complexity": "unknown"}
        self.current_execution["dspy_analysis"] = analysis
        yield create_system_event(
            stage="analysis",
            event="completed",
            text="Task analysis complete",
            payload={"analysis": analysis},
        )

        # --- Routing ----------------------------------------------------------
        team = {name: getattr(agent, "description", name) for name, agent in agents.items()}
        try:
            routing_raw = supervisor.route_task(task, team, context="")
        except Exception:  # pragma: no cover - defensive
            routing_raw = {
                "task": task,
                "assigned_to": list(agents.keys()),
                "mode": ExecutionMode.DELEGATED.value,
                "subtasks": [],
            }

        routing = ensure_routing_decision(routing_raw)

        assigned = [a for a in routing.assigned_to if a in agents]
        if not assigned and agents:
            assigned = [next(iter(agents.keys()))]

        mode = routing.mode
        if mode is ExecutionMode.PARALLEL and len(assigned) <= 1:
            mode = ExecutionMode.DELEGATED

        subtasks = list(routing.subtasks)
        if mode is ExecutionMode.PARALLEL:
            if not subtasks:
                subtasks = [task for _ in assigned]
            elif len(subtasks) < len(assigned):
                subtasks = list(subtasks)
                while len(subtasks) < len(assigned):
                    subtasks.append(task)
            else:
                subtasks = subtasks[: len(assigned)]

        routing = routing.update(
            assigned_to=tuple(assigned),
            mode=mode,
            subtasks=tuple(subtasks),
        )

        routing_dict = routing.to_dict()
        self.current_execution["routing"] = routing_dict
        yield create_system_event(
            stage="routing",
            event="decision",
            text="Routing decision complete",
            payload=routing_dict,
        )

        # --- Execution --------------------------------------------------------
        if mode is ExecutionMode.PARALLEL:
            execution_stream = execute_parallel_streaming(agents, list(assigned), list(subtasks))
        elif len(assigned) == 1:
            execution_stream = execute_delegated_streaming(agents, assigned[0], task)
        else:
            execution_stream = execute_sequential_streaming(
                agents,
                list(assigned),
                task,
                enable_handoffs=self.enable_handoffs,
                handoff_manager=self.handoff_manager,
            )

        result_text: str | None = None
        async for exec_event in execution_stream:
            yield exec_event
            if isinstance(exec_event, WorkflowOutputEvent):
                data = exec_event.data or {}
                if isinstance(data, dict):
                    result_text = str(data.get("result", ""))
                    if data.get("agent_executions"):
                        self.current_execution["agent_executions"] = data["agent_executions"]
                    if data.get("handoff_history"):
                        self.current_execution["handoff_history"] = data["handoff_history"]
                else:
                    result_text = str(data)

        if result_text is None:
            raise RuntimeError("Execution stage did not produce a result")

        self.current_execution["result"] = result_text

        # --- Quality ----------------------------------------------------------
        try:
            quality_raw = supervisor.assess_quality(task=task, result=result_text)
            score = float(quality_raw.get("score", 0.0) or 0.0)
            quality_payload = {
                "score": score,
                "missing": quality_raw.get("missing", ""),
                "improvements": quality_raw.get("improvements", ""),
            }
        except Exception:  # pragma: no cover - defensive
            score = 0.0
            quality_payload = {"score": score, "missing": "", "improvements": ""}

        self.current_execution["quality"] = quality_payload
        yield create_system_event(
            stage="quality",
            event="assessment",
            text=f"Quality score: {quality_payload['score']}",
            payload=quality_payload,
        )

        # --- Progress / refinement -------------------------------------------
        try:
            progress = supervisor.evaluate_progress(task=task, result=result_text)
        except Exception:  # pragma: no cover - defensive
            progress = {"action": "complete", "feedback": ""}

        self.current_execution["progress"] = progress
        yield create_system_event(
            stage="progress",
            event="evaluation",
            text=f"Progress action: {progress.get('action', 'complete')}",
            payload=progress,
        )

        if (
            getattr(config, "enable_refinement", False)
            and score < getattr(config, "refinement_threshold", 8.0)
            and str(progress.get("action", "")).lower().startswith("refine")
            and assigned
        ):
            refine_agent_name = assigned[0]
            agent = agents.get(refine_agent_name)
            if agent is not None:
                refine_prompt = (
                    "Refine these results based on the feedback below.\n\n"
                    f"Task: {task}\n"
                    f"Current result: {result_text}\n\n"
                    f"Feedback: {progress.get('feedback', '')}"
                )
                refined = await agent.run(refine_prompt)
                result_text = str(refined)
                self.current_execution.setdefault("agent_executions", []).append(
                    {"agent": refine_agent_name, "action": "refine"}
                )
                self.current_execution["result"] = result_text
                yield create_system_event(
                    stage="quality",
                    event="refinement",
                    text=f"Refinement completed by {refine_agent_name}",
                    payload={"agent": refine_agent_name},
                )

        quality_report = QualityReport(
            score=float(self.current_execution["quality"].get("score", 0.0) or 0.0),
            missing=str(self.current_execution["quality"].get("missing", "")),
            improvements=str(self.current_execution["quality"].get("improvements", "")),
        )

        final_msg = FinalResultMessage(
            result=result_text,
            routing=routing,
            quality=quality_report,
            judge_evaluations=[],
            execution_summary=getattr(supervisor, "get_execution_summary", lambda: {})(),
            phase_timings={},
            phase_status={},
            metadata={},
        )

        execution_end = datetime.now()
        self.current_execution["end_time"] = execution_end.isoformat()
        self.current_execution["total_time_seconds"] = (
            execution_end - execution_start
        ).total_seconds()

        self.execution_history.append(self.current_execution.copy())
        if self.history_manager is not None:
            self.history_manager.save_execution(self.current_execution)

        yield WorkflowOutputEvent(
            data=self._final_message_to_dict(final_msg), source_executor_id="legacy"
        )

    def _require_supervisor(self):
        """Return supervisor or raise error."""
        if self.dspy_supervisor is None:
            raise RuntimeError("DSPy supervisor not initialized")
        return self.dspy_supervisor

    def _require_agents(self) -> dict[str, Any]:
        """Return agents or raise error."""
        if self.agents is None:
            raise RuntimeError("Agents are not initialized")
        return self.agents

    # ------------------------------------------------------------------
    # Backward-compatibility helpers expected by legacy tests
    # ------------------------------------------------------------------
    def _create_agents(self) -> dict[str, Any]:
        """Create or return prepared agents dictionary.

        In fleet mode the context already owns the agent map; in legacy paths
        we lazily construct the default workflow agents using
        :func:`create_workflow_agents`.  Tests can monkeypatch this method to
        provide lightweight stubs.
        """

        if self.agents is not None:
            return self.agents

        config = self.config or WorkflowConfig()
        ensure_agent_framework_shims()

        if self.tool_registry is None:
            self.tool_registry = ToolRegistry()

        # Legacy path: create agents using the default factory.  The shared
        # OpenAI client is created lazily here; in production the
        # ``initialize_workflow_context`` entrypoint should be preferred.
        from ..utils import create_openai_client_with_store

        openai_client = getattr(self, "openai_client", None)
        if openai_client is None:
            openai_client = create_openai_client_with_store(config.enable_completion_storage)
            self.openai_client = openai_client

        self.agents = create_workflow_agents(
            config=config,
            openai_client=openai_client,
            tool_registry=self.tool_registry,
            create_client_fn=lambda enable_storage: create_openai_client_with_store(enable_storage),
        )
        return self.agents

    def _build_workflow(self) -> Any:
        """Compatibility stub for tests that monkeypatch this method.

        The fleet entrypoint builds workflows via :func:`create_fleet_workflow`;
        direct invocations of this method are reserved for tests.
        """

        if self.workflow is not None:
            return self.workflow
        raise RuntimeError(
            "_build_workflow is a legacy helper; use create_supervisor_workflow in production."
        )

    async def _execute_parallel(self, agent_names: list[str], subtasks: list[str]) -> str:
        """Compatibility wrapper around :func:`execute_parallel`.

        Legacy tests call this method directly; new code uses the higher-level
        execution strategy modules.
        """

        agents = self._require_agents()
        return await execute_parallel(agents, agent_names, subtasks)

    async def _execute_delegated(self, agent_name: str, task: str) -> str:
        """Execute a single agent task (legacy delegated path)."""
        agents = self._require_agents()
        agent = agents.get(agent_name)
        if agent is None:
            from ..exceptions import AgentExecutionError

            raise AgentExecutionError(
                agent_name=agent_name, task=task, original_error=ValueError("Agent not found")
            )
        result_text: str | None = None
        async for event in execute_delegated_streaming(agents, agent_name, task):
            if isinstance(event, WorkflowOutputEvent):
                data = event.data or {}
                result_text = str(data.get("result", "")) if isinstance(data, dict) else str(data)
        if result_text is None:
            raise RuntimeError("Delegated execution did not produce a result")
        return result_text

    async def _execute_sequential(self, agent_names: list[str], task: str) -> str:
        """Execute multiple agents sequentially (legacy path)."""
        agents = self._require_agents()
        result_text: str | None = None
        async for event in execute_sequential_streaming(
            agents,
            agent_names,
            task,
            enable_handoffs=self.enable_handoffs,
            handoff_manager=self.handoff_manager,
        ):
            if isinstance(event, WorkflowOutputEvent):
                data = event.data or {}
                result_text = str(data.get("result", "")) if isinstance(data, dict) else str(data)
        if result_text is None:
            raise RuntimeError("Sequential execution did not produce a result")
        return result_text

    def _normalize_routing_decision(
        self, routing_raw: dict[str, Any], task: str
    ) -> RoutingDecision:
        """Normalize a raw routing decision dict into a RoutingDecision.

        Mirrors the logic used in the legacy execution flow so older tests
        continue to observe identical behaviour.
        """
        routing = ensure_routing_decision(routing_raw)
        agents = self._require_agents()
        assigned = [a for a in routing.assigned_to if a in agents]
        if not assigned and agents:
            assigned = [next(iter(agents.keys()))]
        mode = routing.mode
        if mode is ExecutionMode.PARALLEL and len(assigned) <= 1:
            mode = ExecutionMode.DELEGATED
        subtasks = list(routing.subtasks)
        if mode is ExecutionMode.PARALLEL:
            if not subtasks:
                subtasks = [task for _ in assigned]
            elif len(subtasks) < len(assigned):
                while len(subtasks) < len(assigned):
                    subtasks.append(task)
            else:
                subtasks = subtasks[: len(assigned)]
        return routing.update(assigned_to=tuple(assigned), mode=mode, subtasks=tuple(subtasks))

    def _prepare_subtasks(self, agents: list[str], subtasks: list[str], fallback: str) -> list[str]:
        """Prepare subtasks list to match agent count (pad/truncate)."""
        if not subtasks:
            return [fallback for _ in agents]
        if len(subtasks) < len(agents):
            padded = list(subtasks)
            while len(padded) < len(agents):
                padded.append(fallback)
            return padded
        return list(subtasks[: len(agents)])

    def _synthesize_results(self, results: list[str]) -> str:
        """Combine parallel results into a single string (legacy helper)."""
        return synthesize_results(results)

    async def _refine_results(self, result: str, improvements: str) -> str:
        """Refine results using the Writer agent (legacy helper)."""
        agents = self._require_agents()
        writer = agents.get("Writer")
        if writer is None:
            return result
        refine_prompt = (
            "Refine these results based on the feedback below.\n\n"
            f"Current result: {result}\n\n"
            f"Feedback: {improvements}"
        )
        try:
            refined = await writer.run(refine_prompt)
            return str(refined)
        except Exception:
            return result

    def _validate_tool(self, tool: Any) -> bool:
        """Validate tool for legacy tests (None rejected)."""
        if tool is None:
            return False
        try:
            from ...agents import validate_tool as _vt

            return bool(_vt(tool))
        except Exception:
            return False

    def _create_agent(
        self,
        name: str,
        description: str,
        instructions: str,
        tools: Any | None = None,
    ) -> Any:
        """Minimal agent factory for legacy tests.

        Returns a lightweight object with a ``run`` coroutine; avoids full
        OpenAI client setup when unnecessary in tests.
        """

        class _SimpleAgent:
            def __init__(self, nm: str, desc: str, instr: str, tls: Any | None) -> None:
                self.name = nm
                self.description = desc
                self.instructions = instr
                self.tools = tls

            async def run(self, prompt: str) -> str:  # pragma: no cover - simple stub
                return f"{self.name} output for: {prompt[:100]}"

        return _SimpleAgent(name, description, instructions, tools)

    def _get_supervisor_instructions(self) -> str:
        """Return synthetic supervisor instructions including tool catalog."""
        tool_catalog = (
            self.tool_registry.get_tool_descriptions()
            if self.tool_registry
            else "No tools available"
        )
        return (
            "Supervisor Instructions:\n"
            "You coordinate specialized agents (Researcher, Analyst, Writer, Reviewer, Judge).\n\n"
            "Available tools:\n" + tool_catalog
        )

    def _format_handoff_input(self, handoff: Any) -> str:
        """Delegate to :func:`format_handoff_input` for tests.

        The handoff-aware sequential execution strategy calls this helper
        directly; exposing it on the workflow keeps older tests working while
        the handoff logic lives in :mod:`execution.sequential`.
        """

        return format_handoff_input(handoff)

    def _extract_artifacts(self, result: Any) -> dict[str, Any]:
        """Delegate to :func:`extract_artifacts` for tests."""

        return extract_artifacts(result)

    def _estimate_remaining_work(self, original_task: str, work_done: str) -> str:
        """Delegate to :func:`estimate_remaining_work` for tests."""

        return estimate_remaining_work(original_task, work_done)

    def _derive_objectives(self, remaining_work: str) -> list[str]:
        """Delegate to :func:`derive_objectives` for tests."""

        return derive_objectives(remaining_work)

    async def initialize(self, compile_dspy: bool = True) -> None:
        """Legacy initialization used by older tests.

        New code should use :func:`agentic_fleet.workflows.supervisor_workflow.
        create_supervisor_workflow`.  This method configures environment
        shims, agents, the tool registry, handoff manager, and optionally
        kicks off background DSPy compilation using the legacy
        ``compile_supervisor`` hook that tests patch.
        """

        config = self.config or WorkflowConfig()
        self.config = config

        ensure_agent_framework_shims()
        validate_agentic_fleet_env()

        # Ensure we have agents available (tests may monkeypatch
        # ``_create_agents``).
        self.agents = self._create_agents()

        # Attach tool registry to supervisor when present.
        from .. import supervisor_workflow as _supervisor_module

        if self.dspy_supervisor is None:
            from ...dspy_modules.supervisor import DSPySupervisor

            self.dspy_supervisor = DSPySupervisor(use_enhanced_signatures=True)

        if self.tool_registry is None:
            self.tool_registry = ToolRegistry()

        if hasattr(self.dspy_supervisor, "set_tool_registry"):
            self.dspy_supervisor.set_tool_registry(self.tool_registry)

        # Set up handoff manager, preferring compiled supervisor chains when
        # available via the ``compiled_supervisor`` property.
        self.handoff_manager = HandoffManager(
            self.dspy_supervisor,
            get_compiled_supervisor=lambda: self.compiled_supervisor,
        )

        self.enable_handoffs = bool(getattr(config, "enable_handoffs", True))

        # Analysis cache controlled by config.
        if getattr(config, "analysis_cache_ttl_seconds", 0) > 0:
            self.analysis_cache = TTLCache[str, dict[str, Any]](config.analysis_cache_ttl_seconds)

        # Start background compilation if requested.  Tests patch
        # ``compile_supervisor`` in the ``supervisor_workflow`` module.
        compile_fn = getattr(_supervisor_module, "compile_supervisor", None)

        if compile_dspy and getattr(config, "compile_dspy", False) and compile_fn is not None:
            self._compilation_status = "compiling"

            async def _run_compile() -> None:
                try:
                    loop = asyncio.get_event_loop()

                    def _compile_sync() -> Any:
                        return compile_fn(self.dspy_supervisor, config, self.agents)

                    compiled = await loop.run_in_executor(None, _compile_sync)
                    self._compiled_supervisor = compiled
                    self._compilation_status = "completed"
                except Exception:  # pragma: no cover - failure path exercised separately
                    logger.exception("DSPy compilation failed in background task")
                    self._compiled_supervisor = self.dspy_supervisor
                    self._compilation_status = "failed"

            self._compilation_task = asyncio.create_task(_run_compile())
        else:
            self._compilation_status = (
                "skipped" if not getattr(config, "compile_dspy", False) else "pending"
            )

    @property
    def compiled_supervisor(self) -> Any:
        """Return the compiled supervisor, triggering sync compilation if needed.

        This mirrors the behaviour of the original implementation closely
        enough for the lazy compilation tests while delegating the actual
        compilation work to the shimmed ``compile_supervisor`` function.
        """

        if self._compiled_supervisor is not None and self._compilation_status == "completed":
            return self._compiled_supervisor

        # If a background task exists, prefer its result when finished.
        if self._compilation_task is not None:
            if self._compilation_task.done():
                return self._compiled_supervisor or self.dspy_supervisor
            # Event loop running - don't block, fall back to uncompiled supervisor.
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.run_until_complete(self._compilation_task)
                    return self._compiled_supervisor or self.dspy_supervisor
            except RuntimeError:
                return self.dspy_supervisor
            return self.dspy_supervisor

        # No compilation has started yet - perform a synchronous compilation
        # if configuration allows it or the property is accessed explicitly.
        if self._compilation_status in {"pending", "skipped"}:
            try:
                from .. import supervisor_workflow as _supervisor_module

                compile_fn = getattr(_supervisor_module, "compile_supervisor", None)
                if compile_fn is not None:
                    config = self.config or WorkflowConfig()
                    compiled = compile_fn(self.dspy_supervisor, config, self.agents)
                    self._compiled_supervisor = compiled
                    self._compilation_status = "completed"
                    return compiled
            except Exception:  # pragma: no cover - failure path exercised in tests
                logger.exception("Synchronous DSPy compilation failed")
                self._compilation_status = "failed"

        # Fallback to the uncompiled supervisor.
        return self._compiled_supervisor or self.dspy_supervisor


async def create_fleet_workflow(
    context: SupervisorContext,
    compile_dspy: bool = True,
) -> SupervisorWorkflow:
    """Create and initialize the supervisor workflow.

    Args:
        context: Supervisor context with configuration and state
        compile_dspy: Whether to compile DSPy supervisor (unused, kept for compatibility)

    Returns:
        SupervisorWorkflow instance
    """
    # Maintain async signature for future extensibility; satisfy lint by explicit await.
    await asyncio.sleep(0)
    supervisor = context.dspy_supervisor
    if supervisor is None:
        raise RuntimeError("DSPy supervisor must be initialized in context")

    # Ensure supervisor has tool registry
    if context.tool_registry and not supervisor.tool_registry:
        supervisor.set_tool_registry(context.tool_registry)

    # Build workflow using WorkflowBuilder
    workflow_builder = build_fleet_workflow(supervisor, context)

    # Build workflow and wrap as agent
    workflow = workflow_builder.build()

    # Create workflow entrypoint
    workflow = SupervisorWorkflow(context, workflow)

    logger.info("Supervisor workflow created successfully")
    return workflow
