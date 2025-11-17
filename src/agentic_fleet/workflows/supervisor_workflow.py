"""Compatibility shim exposing legacy SupervisorWorkflow API.

Bridges older tests to the new fleet workflow by providing:
- SupervisorWorkflow with initialize/compilation helpers
- WorkflowConfig re-export
- compile_supervisor symbol to allow patching in tests
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from ..dspy_modules.supervisor import DSPySupervisor
from ..utils.logger import setup_logger
from ..utils.tool_registry import ToolRegistry
from .config import WorkflowConfig
from .fleet.adapter import create_fleet_workflow
from .initialization import initialize_workflow_context

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
        self, config: WorkflowConfig | None = None, workflow_runner: Any | None = None, **_: Any
    ) -> None:
        # Public attributes referenced by tests
        self.config = config or WorkflowConfig()
        self.workflow_runner = workflow_runner
        self.tool_registry: ToolRegistry | None = None
        self.dspy_supervisor: DSPySupervisor = DSPySupervisor(use_enhanced_signatures=True)
        self._compiled_supervisor: DSPySupervisor | None = None
        self._compilation_task: asyncio.Task[None] | None = None
        self._compilation_status: str = "pending"
        self._agents: dict[str, Any] | None = None
        self._context: Any | None = None

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
        self.tool_registry = context.tool_registry
        self._agents = context.agents
        # Keep reference to the live (uncompiled) supervisor
        self.dspy_supervisor = context.dspy_supervisor
        # Mirror compilation status for tests
        self._compilation_task = context.compilation_task
        self._compilation_status = context.compilation_status or "pending"

        if compile_dspy and self._compilation_task is None:
            # Fallback: if not already scheduled (should be in normal flow),
            # spin up a background task using the local compile_supervisor symbol
            logger.info("Scheduling background compilation task (compatibility path)")
            self._compilation_task = asyncio.create_task(self._compile_background())
            self._compilation_status = "compiling"

    # ------------------- Minimal legacy execution API -------------------
    async def run(self, task: str) -> dict[str, Any]:
        """Simplified run compatible with legacy tests."""
        team = {
            name: getattr(agent, "description", name) for name, agent in (self.agents or {}).items()
        }
        routing = self.dspy_supervisor.route_task(task, team, "")
        assigned = list(routing.get("assigned_to", [])) if isinstance(routing, dict) else []
        mode = (
            routing.get("mode", "delegated") if isinstance(routing, dict) else "delegated"
        ).lower()
        subtasks = list(routing.get("subtasks", [])) if isinstance(routing, dict) else []

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
            # Normalize subtasks count (pad with base task)
            if len(subtasks) < len(assigned):
                subtasks = subtasks + [task] * (len(assigned) - len(subtasks))
            result_text = await self._execute_parallel(assigned, subtasks)
        else:
            # Delegated/sequential -> first agent handles the task
            agent_id = assigned[0] if assigned else (agent_names[0] if agent_names else "")
            agent = (self.agents or {}).get(agent_id)
            result_text = await agent.run(task) if agent else ""

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
        """Execute tasks in parallel across assigned agents; handle failures gracefully."""

        async def run_single(agent_id: str, subtask: str) -> str:
            agent = (self.agents or {}).get(agent_id)
            try:
                return await agent.run(subtask) if agent else f"{agent_id} failed: missing agent"
            except Exception:
                return f"{agent_id} failed: error"

        coros = [run_single(a, s) for a, s in zip(assigned, subtasks, strict=False)]
        results = await asyncio.gather(*coros, return_exceptions=False)
        return " | ".join(results)

    async def run_stream(self, task: str):
        """Simplified streaming: yield a single WorkflowOutputEvent with final dict."""
        from agent_framework import WorkflowOutputEvent  # test stub

        # Minimal tracking for tests
        self.current_execution = {"routing": {"subtasks": []}}

        # Get routing to expose normalized subtasks in current_execution
        team = {
            name: getattr(agent, "description", name) for name, agent in (self.agents or {}).items()
        }
        routing = self.dspy_supervisor.route_task(task, team, "")
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
        """Return compiled supervisor if available, else uncompiled."""
        # If completed and we have it, return compiled
        if self._compiled_supervisor is not None and self._compilation_status == "completed":
            return self._compiled_supervisor

        # If a task exists and we're not in a running loop, block until done
        if self._compilation_task and not self._compilation_task.done():
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # In running loop, do not block (return base)
                    return self.dspy_supervisor
                loop.run_until_complete(self._compilation_task)
            except RuntimeError:
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
        return f"{original}\n[Refined based on: {improvements}]"

    def _create_agent(self, name: str, description: str = "", tools: Any = None) -> Any:
        """Create an agent instance (legacy helper for tests)."""
        from types import SimpleNamespace

        class _Agent:
            def __init__(self, n: str, d: str = "", t: Any = None):
                self.name = n
                self.description = d or n
                self.chat_options = SimpleNamespace(
                    tools=t if isinstance(t, list) else ([t] if t else [])
                )

            async def run(self, task: str) -> str:
                return f"{self.name}:{task}"

        return _Agent(name, description, tools)


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
