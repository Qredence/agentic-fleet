"""Compatibility shim exposing legacy SupervisorWorkflow API.

Bridges older tests to the new fleet workflow by providing:
- SupervisorWorkflow with initialize/compilation helpers
- WorkflowConfig re-export
- compile_supervisor symbol to allow patching in tests
"""

from __future__ import annotations

import asyncio
import textwrap
from typing import TYPE_CHECKING, Any

from ..dspy_modules.supervisor import DSPySupervisor
from ..utils.agent_framework_shims import ensure_agent_framework_shims
from ..utils.logger import setup_logger
from ..utils.tool_registry import ToolRegistry
from .config import WorkflowConfig
from .execution.delegated import execute_delegated
from .execution.parallel import execute_parallel
from .execution.sequential import execute_sequential, format_handoff_input
from .fleet.adapter import create_fleet_workflow
from .handoff_manager import HandoffContext, HandoffManager
from .initialization import initialize_workflow_context
from .utils import derive_objectives, estimate_remaining_work, extract_artifacts

if TYPE_CHECKING:
    from .fleet.adapter import FleetWorkflow as _SupervisorWorkflowType

logger = setup_logger(__name__)


# Tests patch this symbol from this module, so provide it here.
def compile_supervisor(  # pragma: no cover - used via test patches
    supervisor: DSPySupervisor,
    examples_path: str,
    optimizer: str,
    gepa_options: dict[str, Any] | None,
    dspy_model: str,
    agent_config: dict[str, Any],
    progress_callback: Any | None = None,
) -> DSPySupervisor:
    """Proxy symbol for test patching; real implementation lives in utils.compiler."""
    from ..utils.compiler import compile_supervisor as _real_compile

    return _real_compile(
        supervisor,
        examples_path=examples_path,
        optimizer=optimizer,
        gepa_options=gepa_options,
        dspy_model=dspy_model,
        agent_config=agent_config,
        progress_callback=progress_callback,
    )


class SupervisorWorkflow:
    """Legacy-compatible SupervisorWorkflow facade."""

    def __init__(
        self,
        config: WorkflowConfig | None = None,
        workflow_runner: Any | None = None,
        **kwargs: Any,
    ) -> None:
        ensure_agent_framework_shims()
        # Allow tests/legacy callers to pass alternate initialization kwargs without errors.
        custom_agents = kwargs.pop("agents", None)
        custom_supervisor = kwargs.pop("dspy_supervisor", None)
        custom_registry: ToolRegistry | None = kwargs.pop("tool_registry", None)
        custom_handoff_manager: HandoffManager | None = kwargs.pop("handoff_manager", None)

        self.config = config or WorkflowConfig()
        self.workflow_runner = workflow_runner
        self.tool_registry: ToolRegistry = custom_registry or ToolRegistry()
        self.dspy_supervisor: DSPySupervisor = custom_supervisor or DSPySupervisor(
            use_enhanced_signatures=True
        )
        self._compiled_supervisor: DSPySupervisor | None = None
        self._compilation_task: asyncio.Task[None] | None = None
        self._compilation_status: str = "pending"
        self._agents: dict[str, Any] | None = custom_agents
        self._context: Any | None = None
        self.current_execution: dict[str, Any] = {}
        self.execution_history: list[dict[str, Any]] = []
        self._handoff_manager: HandoffManager | None = custom_handoff_manager
        self._enable_handoffs: bool = self.config.enable_handoffs

        # Minimal history manager stub
        class _Hist:
            async def save_execution(self, *_: Any, **__: Any) -> str:
                return ""

        self.history_manager = _Hist()

    async def initialize(self, compile_dspy: bool = True) -> None:
        """Initialize agents, tools, and optionally start background compilation."""
        logger.info("Initializing legacy SupervisorWorkflow facade...")
        # Reuse shared initialization utilities
        context = await initialize_workflow_context(config=self.config, compile_dspy=compile_dspy)
        self._context = context
        self.tool_registry = context.tool_registry or self.tool_registry
        self._agents = context.agents
        # Keep reference to the live (uncompiled) supervisor
        self.dspy_supervisor = context.dspy_supervisor
        # Mirror compilation status for tests
        self._compilation_task = context.compilation_task
        self._compilation_status = context.compilation_status or "pending"
        self.history_manager = context.history_manager or self.history_manager
        self.execution_history = context.execution_history
        self.current_execution = context.current_execution
        self.handoff_manager = context.handoff_manager or self._handoff_manager
        self._enable_handoffs = context.enable_handoffs

        if compile_dspy and self._compilation_task is None:
            # Fallback: if not already scheduled (should be in normal flow),
            # spin up a background task using the local compile_supervisor symbol
            logger.info("Scheduling background compilation task (compatibility path)")
            self._compilation_task = asyncio.create_task(self._compile_background())
            self._compilation_status = "compiling"

    # ------------------- Minimal legacy execution API -------------------
    @property
    def agents(self) -> dict[str, Any] | None:
        """Public accessor for agents."""
        return self._agents

    @agents.setter
    def agents(self, value: dict[str, Any] | None) -> None:
        self._agents = value

    @property
    def enable_handoffs(self) -> bool:
        return self._enable_handoffs

    @enable_handoffs.setter
    def enable_handoffs(self, value: bool) -> None:
        flag = bool(value)
        self._enable_handoffs = flag
        self.config.enable_handoffs = flag
        if self._context is not None:
            self._context.enable_handoffs = flag

    @property
    def handoff_manager(self) -> HandoffManager | None:
        if self._handoff_manager is None and self.dspy_supervisor is not None:
            self._handoff_manager = HandoffManager(self.dspy_supervisor)
            self._bind_handoff_manager(self._handoff_manager)
        return self._handoff_manager

    @handoff_manager.setter
    def handoff_manager(self, manager: HandoffManager | None) -> None:
        self._handoff_manager = manager
        if manager is not None:
            self._bind_handoff_manager(manager)

    def _bind_handoff_manager(self, manager: HandoffManager) -> None:
        if getattr(manager, "_workflow_bound", False):
            return

        base_provider = getattr(manager, "_get_compiled_supervisor", None)

        def _provider():
            if self._compiled_supervisor is not None:
                return self._compiled_supervisor
            if callable(base_provider):
                try:
                    candidate = base_provider()
                    if candidate is not None:
                        return candidate
                except Exception:  # pragma: no cover - defensive guardrail
                    logger.debug("Handoff provider fallback failed", exc_info=True)
            return self.dspy_supervisor

        manager._get_compiled_supervisor = _provider  # type: ignore[attr-defined]
        manager._workflow_bound = True

    # ------------------- Minimal legacy execution API -------------------
    async def run(self, task: str) -> dict[str, Any]:
        """Simplified run compatible with legacy tests."""
        team = {
            name: getattr(agent, "description", name) for name, agent in (self.agents or {}).items()
        }
        routing_raw = self.dspy_supervisor.route_task(task, team, "")
        routing = self._routing_to_dict(routing_raw)
        assigned = list(routing.get("assigned_to", []))
        mode = str(routing.get("mode", "delegated")).lower()
        subtasks = list(routing.get("subtasks", []))

        # Fallback unknown agents to first available
        agent_names = list((self.agents or {}).keys())
        if assigned:
            normalized = []
            for a in assigned:
                if a in (self.agents or {}):
                    normalized.append(a)
            if not normalized and agent_names:
                normalized = [agent_names[0]]
            assigned = normalized
        elif agent_names:
            assigned = [agent_names[0]]

        # Convert single-agent parallel to delegated
        if mode == "parallel" and len(assigned) <= 1:
            mode = "delegated"

        if mode == "parallel":
            subtasks = self._prepare_subtasks(assigned, subtasks, task)
            result_text = await self._execute_parallel(assigned, subtasks)
        elif mode == "sequential":
            result_text = await self._execute_sequential(assigned, task)
        else:
            agent_id = assigned[0] if assigned else (agent_names[0] if agent_names else "")
            if not agent_id:
                result_text = ""
            else:
                result_text = await self._execute_delegated(agent_id, task)

        # Build legacy-like result
        return {
            "result": result_text,
            "routing": {"assigned_to": assigned, "mode": mode, "subtasks": subtasks},
            "quality": {"score": 10.0, "used_fallback": False},
            "judge_evaluations": [],
            "execution_summary": self.dspy_supervisor.get_execution_summary(),
            "phase_timings": {},
            "phase_status": {},
        }

    async def _execute_parallel(self, assigned: list[str], subtasks: list[str]) -> str:
        return await execute_parallel(self.agents or {}, assigned, subtasks)

    async def _execute_sequential(self, agents: list[str], task: str) -> str:
        return await execute_sequential(
            self.agents or {},
            agents,
            task,
            enable_handoffs=self.enable_handoffs,
            handoff_manager=self.handoff_manager,
        )

    async def _execute_delegated(self, agent_name: str, task: str) -> str:
        return await execute_delegated(self.agents or {}, agent_name, task)

    async def run_stream(self, task: str):
        """Simplified streaming: yield a single WorkflowOutputEvent with final dict."""
        ensure_agent_framework_shims()
        from agent_framework import WorkflowOutputEvent  # test stub

        # Minimal tracking for tests
        self.current_execution = {"routing": {"subtasks": []}}

        # Get routing to expose normalized subtasks in current_execution
        team = {
            name: getattr(agent, "description", name) for name, agent in (self.agents or {}).items()
        }
        routing_raw = self.dspy_supervisor.route_task(task, team, "")
        routing = self._routing_to_dict(routing_raw)
        assigned = list(routing.get("assigned_to", []))
        subtasks = list(routing.get("subtasks", []))
        if len(subtasks) < len(assigned):
            subtasks = subtasks + [task] * (len(assigned) - len(subtasks))
        self.current_execution["routing"]["subtasks"] = subtasks

        final = await self.run(task)
        yield WorkflowOutputEvent(data=final, source_executor_id="fleet")

    async def _compile_background(self) -> None:
        """Background compilation using the proxy symbol for patchability."""
        try:
            # Extract agent config similar to utils/compilation.py
            agent_config: dict[str, Any] = {}
            for agent_name, agent in (self._agents or {}).items():
                tools = []
                if hasattr(agent, "chat_options") and getattr(agent.chat_options, "tools", None):
                    tools = [t.__class__.__name__ for t in (agent.chat_options.tools or []) if t]
                agent_config[agent_name] = {
                    "description": getattr(agent, "description", ""),
                    "tools": tools,
                }

            compiled = compile_supervisor(
                self.dspy_supervisor,
                examples_path=self.config.examples_path,
                optimizer=self.config.dspy_optimizer,
                gepa_options=self.config.gepa_options,
                dspy_model=self.config.dspy_model,
                agent_config=agent_config,
                progress_callback=None,
            )
            self._compiled_supervisor = compiled
            self._compilation_status = "completed"
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Background compilation failed: {e}")
            self._compiled_supervisor = self.dspy_supervisor
            self._compilation_status = "failed"

    @property
    def compiled_supervisor(self) -> DSPySupervisor:
        if self._compilation_task and not self._compilation_task.done():
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(self._compilation_task)
                except Exception:
                    return self.dspy_supervisor
                finally:
                    loop.close()
            else:
                # In an active event loop; avoid blocking
                return self.dspy_supervisor

        # If compilation hasn't started (pending) and no task, trigger synchronous compile (legacy behavior)
        if self._compilation_task is None and self._compilation_status in ("pending", "skipped"):
            try:
                # Build minimal agent config for cache key stability
                agent_config: dict[str, Any] = {}
                for agent_name, agent in (self._agents or {}).items():
                    tools = []
                    if hasattr(agent, "chat_options") and getattr(
                        agent.chat_options, "tools", None
                    ):
                        tools = [
                            t.__class__.__name__ for t in (agent.chat_options.tools or []) if t
                        ]
                    agent_config[agent_name] = {
                        "description": getattr(agent, "description", ""),
                        "tools": tools,
                    }
                compiled = compile_supervisor(  # type: ignore[misc]
                    self.dspy_supervisor,
                    examples_path=self.config.examples_path
                    if self.config
                    else "data/supervisor_examples.json",
                    optimizer=self.config.dspy_optimizer if self.config else "bootstrap",
                    gepa_options=self.config.gepa_options if self.config else None,
                    dspy_model=self.config.dspy_model if self.config else "gpt-5-mini",
                    agent_config=agent_config,
                    progress_callback=None,
                )
                self._compiled_supervisor = compiled
                self._compilation_status = "completed"
                return compiled
            except Exception:
                self._compilation_status = "failed"
                return self.dspy_supervisor

        # Return compiled if set; else fallback to base
        return self._compiled_supervisor or self.dspy_supervisor

    # -------- Tool validation helpers used in tests --------
    def _validate_tool(self, tool: Any) -> bool:
        """Validate a tool-like object for registration."""
        if tool is None:
            return False
        # Accept dict schemas (OpenAI function-call style)
        if isinstance(tool, dict):
            return "type" in tool or "function" in tool
        # Accept callable (legacy)
        if callable(tool):
            return True
        # Accept agent-framework ToolProtocol/SerializationMixin style
        has_schema = hasattr(tool, "schema") or hasattr(tool, "to_dict")
        has_name_desc = hasattr(tool, "name") and hasattr(tool, "description")
        return bool(has_schema or has_name_desc)

    # Legacy helper expected by some tests
    def _create_agents(self) -> dict[str, Any]:
        # Provide a minimal Researcher agent without tools when none are configured
        if self._agents is not None:
            return self._agents
        # Ensure a tool registry exists
        if self.tool_registry is None:
            self.tool_registry = ToolRegistry()

        class _Agent:
            def __init__(self, name: str):
                self.name = name
                self.description = name
                from types import SimpleNamespace

                self.chat_options = SimpleNamespace(tools=[])

            async def run(self, task: str) -> str:
                return f"{self.name}:{task}"

        self._agents = {"Researcher": _Agent("Researcher")}
        return self._agents

    def _build_workflow(self) -> Any:
        """Build workflow (legacy helper for tests)."""
        if self.workflow_runner is not None:
            return self.workflow_runner

        # Create a minimal workflow stub
        class _WorkflowStub:
            async def run(self, task: str) -> dict[str, Any]:
                return {"result": f"stub:{task}", "metadata": {}}

            async def run_stream(self, task: str):
                ensure_agent_framework_shims()
                from agent_framework import WorkflowOutputEvent

                yield WorkflowOutputEvent(
                    data={"result": f"stub:{task}"}, source_executor_id="stub"
                )

        return _WorkflowStub()

    def _normalize_routing_decision(self, routing: dict[str, Any], task: str) -> Any:
        """Normalize routing decision (legacy helper for tests)."""
        from ..utils.models import ExecutionMode, RoutingDecision

        assigned_raw = routing.get("assigned_to", [])
        if isinstance(assigned_raw, str):
            assigned_list = [a.strip() for a in assigned_raw.split(",") if a.strip()]
        elif isinstance(assigned_raw, list | tuple):
            assigned_list = list(assigned_raw)
        else:
            assigned_list = []
        # Fallback to first available agent if none match
        agents = self._agents or {}
        team_keys = list(agents.keys())
        normalized_agents = []
        for agent_name in assigned_list:
            if agent_name in team_keys:
                normalized_agents.append(agent_name)
        if not normalized_agents and team_keys:
            normalized_agents = [team_keys[0]]
        mode_str = routing.get("mode", "delegated")
        mode = ExecutionMode.from_raw(mode_str)
        # Convert parallel to delegated for single agent
        if mode is ExecutionMode.PARALLEL and len(normalized_agents) == 1:
            mode = ExecutionMode.DELEGATED
        if mode is ExecutionMode.DELEGATED and len(normalized_agents) > 1:
            normalized_agents = normalized_agents[:1]
        return RoutingDecision(
            task=task,
            assigned_to=tuple(normalized_agents),
            mode=mode,
            subtasks=tuple(routing.get("subtasks", [])),
            tool_requirements=tuple(routing.get("tool_requirements", [])),
            confidence=routing.get("confidence"),
        )

    def _prepare_subtasks(self, agents: list[str], subtasks: list[str], fallback: str) -> list[str]:
        """Prepare subtasks aligned with agents (legacy helper for tests)."""
        if len(subtasks) < len(agents):
            return subtasks + [fallback] * (len(agents) - len(subtasks))
        return subtasks[: len(agents)]

    def _synthesize_results(self, results: list[str]) -> str:
        """Synthesize multiple results (legacy helper for tests)."""
        return " | ".join(results)

    async def _refine_results(self, original: str, improvements: str) -> str:
        """Refine results based on improvements (legacy helper for tests)."""
        writer = None
        for name, agent in (self.agents or {}).items():
            if name.lower() == "writer":
                writer = agent
                break

        if writer is None or not hasattr(writer, "run"):
            return f"{original}\n[Refined based on: {improvements}]"

        refinement_prompt = textwrap.dedent(
            f"""
            Please refine the following result using the requested improvements.

            ## Current Result
            {original}

            ## Requested Improvements
            {improvements}

            Return only the refined result.
            """
        ).strip()

        try:
            refined = await writer.run(refinement_prompt)
            if isinstance(refined, str) and refined.strip():
                return refined
        except Exception:  # pragma: no cover - fallback on failure
            logger.warning("Writer agent refinement failed; returning fallback result.")

        return f"{original}\n[Refined based on: {improvements}]"

    def _routing_to_dict(self, routing: Any) -> dict[str, Any]:
        """Normalize routing decision objects to a dict structure."""
        if isinstance(routing, dict):
            return dict(routing)
        if hasattr(routing, "_asdict"):
            try:
                return dict(routing._asdict())  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover - defensive
                pass
        if hasattr(routing, "__dict__"):
            data = {}
            for attr in ("assigned_to", "mode", "subtasks", "tool_requirements", "confidence"):
                if hasattr(routing, attr):
                    data[attr] = getattr(routing, attr)
            return data
        return {}

    def _format_handoff_input(self, handoff: HandoffContext) -> str:
        """Format handoff context for next agent (legacy helper)."""
        return format_handoff_input(handoff)

    def _extract_artifacts(self, result: Any) -> dict[str, Any]:
        """Extract artifacts from agent result (legacy helper)."""
        return extract_artifacts(result)

    def _estimate_remaining_work(self, original_task: str, work_done: str) -> str:
        """Estimate remaining work based on original task and completed work."""
        return estimate_remaining_work(original_task, work_done)

    def _derive_objectives(self, remaining_work: str) -> list[str]:
        """Derive objectives from remaining work description."""
        return derive_objectives(remaining_work)

    def _create_agent(
        self,
        name: str,
        description: str = "",
        instructions: str | None = None,
        tools: Any = None,
    ) -> Any:
        """Create an agent instance (legacy helper for tests)."""
        from types import SimpleNamespace

        class _Agent:
            def __init__(self, n: str, d: str = "", i: str | None = None, t: Any = None):
                self.name = n
                self.description = d or n
                self.instructions = i
                self.chat_options = SimpleNamespace(
                    tools=t if isinstance(t, list) else ([t] if t else [])
                )

            async def run(self, task: str) -> str:
                return f"{self.name}:{task}"

        return _Agent(name, description, instructions, tools)

    def _get_supervisor_instructions(self) -> str:
        agent_lines = []
        for name, agent in (self.agents or {}).items():
            desc = getattr(agent, "description", name)
            agent_lines.append(f"- {name}: {desc}")
        roster = "\n".join(agent_lines) if agent_lines else "- No agents registered."

        tool_catalog = (
            self.tool_registry.get_tool_descriptions()
            if hasattr(self.tool_registry, "get_tool_descriptions")
            else "No tools are currently available."
        )

        return textwrap.dedent(
            f"""
            ## Team Roster
            {roster}

            ## Available Tools
            {tool_catalog}
            """
        ).strip()


# -----------------------------------------------------------------------------
# Backward-compatibility exports used by CLI and comprehensive tests
# -----------------------------------------------------------------------------


def _validate_task(task: str, *, max_length: int = 10000) -> str:
    """Validate a task string (legacy helper)."""
    if not task or not task.strip():
        raise ValueError("Task cannot be empty")
    if len(task) > max_length:
        raise ValueError(f"Task exceeds maximum length of {max_length} characters")
    return task.strip()


async def create_supervisor_workflow(
    compile_dspy: bool = True,
    config: WorkflowConfig | None = None,
) -> _SupervisorWorkflowType:
    """Factory function to create and initialize supervisor workflow (legacy export)."""
    # Initialize workflow context
    context = await initialize_workflow_context(config=config, compile_dspy=compile_dspy)
    # Create workflow entrypoint
    workflow = await create_fleet_workflow(context, compile_dspy=compile_dspy)
    return workflow
