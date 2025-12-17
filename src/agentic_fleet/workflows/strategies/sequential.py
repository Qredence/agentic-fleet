"""Sequential execution strategy (with optional handoffs)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework._agents import ChatAgent
from agent_framework._threads import AgentThread
from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import WorkflowOutputEvent

from ...utils.logger import setup_logger
from ...utils.models import ExecutionMode, RoutingDecision
from ..exceptions import AgentExecutionError
from ..handoff import HandoffContext, HandoffManager
from ..helpers import (
    derive_objectives,
    estimate_remaining_work,
    extract_artifacts,
)
from ..models import MagenticAgentMessageEvent
from .base import (
    ExecutionPhaseError,
    _extract_tool_usage,
    _get_agent,
    create_agent_event,
    create_system_event,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ...utils.progress import ProgressCallback
    from ..context import SupervisorContext

logger = setup_logger(__name__)


async def _execute_sequential_helper(
    *,
    agents_map: dict[str, Any],
    agents: list[str],
    task: str,
    enable_handoffs: bool,
    handoff_manager: HandoffManager | None,
) -> tuple[str, list[dict[str, Any]]]:
    if not agents:
        raise ExecutionPhaseError("Sequential execution requires at least one agent.")

    if enable_handoffs and handoff_manager:
        return await execute_sequential_with_handoffs(
            agents_map,
            list(agents),
            task,
            handoff_manager,
        )

    # Simple mode is disabled by default; can be enabled in future with executor metadata analysis
    simple_mode = False
    return await execute_sequential(
        agents_map,
        list(agents),
        task,
        enable_handoffs=False,
        handoff=None,
        simple_mode=simple_mode,
    )


class SequentialExecutionStrategy:
    """Execute work step-by-step across multiple agents."""

    mode = ExecutionMode.SEQUENTIAL

    async def execute(
        self,
        *,
        routing: RoutingDecision,
        task: str,
        context: SupervisorContext,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Execute the routing decision without streaming."""
        agents_map = context.agents or {}
        return await _execute_sequential_helper(
            agents_map=agents_map,
            agents=list(routing.assigned_to),
            task=task,
            enable_handoffs=context.enable_handoffs,
            handoff_manager=context.handoff,
        )

    async def stream(
        self,
        *,
        routing: RoutingDecision,
        task: str,
        context: SupervisorContext,
    ) -> AsyncIterator[MagenticAgentMessageEvent | WorkflowOutputEvent]:
        """Stream execution events for the routing decision."""
        agents_map = context.agents or {}
        async for event in execute_sequential_streaming(
            agents_map,
            list(routing.assigned_to),
            task,
            progress_callback=context.progress_callback,
            enable_handoffs=context.enable_handoffs,
            handoff=context.handoff,
            thread=context.conversation_thread,
        ):
            yield event


def format_handoff_input(handoff: HandoffContext) -> str:
    """Format handoff context as structured input for next agent."""
    return f"""
# HANDOFF FROM {handoff.from_agent}

## Work Completed
{handoff.work_completed}

## Your Objectives
{chr(10).join(f"- {obj}" for obj in handoff.remaining_objectives)}

## Success Criteria
{chr(10).join(f"- {crit}" for crit in handoff.success_criteria)}

## Available Artifacts
{chr(10).join(f"- {k}: {v}" for k, v in handoff.artifacts.items())}

## Quality Checklist
{chr(10).join(f"- [ ] {item}" for item in handoff.quality_checklist)}

## Required Tools
{", ".join(handoff.tool_requirements) if handoff.tool_requirements else "None"}

---
Please continue the work based on the above context.
"""


async def execute_sequential(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    task: str,
    enable_handoffs: bool = False,
    handoff: HandoffManager | None = None,
    *,
    simple_mode: bool | None = None,
    thread: AgentThread | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Execute a task sequentially across agents without streaming."""
    if not agent_names:
        raise AgentExecutionError(
            agent_name="unknown",
            task="sequential execution",
            original_error=RuntimeError("Sequential execution requires at least one agent"),
        )

    # Use handoff-enabled execution if available
    if enable_handoffs and handoff:
        return await execute_sequential_with_handoffs(
            agents,
            agent_names,
            task,
            handoff,
            thread=thread,
        )

    # Standard sequential execution (original behavior)
    result: Any = task
    aggregated_usage = []

    for agent_name in agent_names:
        agent = _get_agent(agents, agent_name)
        if not agent:
            logger.warning(
                "Skipping unknown agent '%s' during sequential execution",
                agent_name,
            )
            continue
        # Prevent heavy tools on simple tasks: if simple_mode is set, avoid
        # tool-triggering formats and just ask the agent directly.
        try:
            if simple_mode:
                # Pass result directly without string conversion
                if thread is None:
                    response = await agent.run(result)
                else:
                    response = await agent.run(result, thread=thread)
            else:
                if thread is None:
                    response = await agent.run(str(result))
                else:
                    response = await agent.run(str(result), thread=thread)
        except Exception as exc:
            logger.warning("Agent '%s' failed during sequential execution: %s", agent_name, exc)
            result = f"{result}\n\n[{agent_name} failed: {exc!s}]"
            continue

        aggregated_usage.extend(_extract_tool_usage(response))
        result = str(response)

    return str(result), aggregated_usage


async def execute_sequential_with_handoffs(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    task: str,
    handoff: HandoffManager,
    *,
    thread: AgentThread | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Execute sequential workflow with intelligent handoffs.

    This method uses the HandoffManager to create structured handoffs
    between agents with rich context, artifacts, and quality criteria.
    """
    result = task
    artifacts: dict[str, Any] = {}
    aggregated_usage = []

    for i, current_agent_name in enumerate(agent_names):
        agent = _get_agent(agents, current_agent_name)
        if not agent:
            logger.warning(f"Skipping unknown agent '{current_agent_name}'")
            continue

        # Execute current agent's work
        logger.info(f"Agent {current_agent_name} starting work")
        try:
            if thread is None:
                agent_result = await agent.run(str(result))
            else:
                agent_result = await agent.run(str(result), thread=thread)
        except Exception as exc:
            logger.warning(
                "Agent '%s' failed during handoff sequential execution: %s",
                current_agent_name,
                exc,
            )
            result = f"{result}\n\n[{current_agent_name} failed: {exc!s}]"
            continue
        aggregated_usage.extend(_extract_tool_usage(agent_result))

        # Extract artifacts from result (simplified - could be more sophisticated)
        current_artifacts = extract_artifacts(agent_result)
        artifacts.update(current_artifacts)

        # Check if handoff is needed (before last agent)
        if i < len(agent_names) - 1:
            next_agent_name = agent_names[i + 1]
            remaining_work = estimate_remaining_work(task, str(agent_result))

            # Evaluate if handoff should proceed
            available_agents_map: dict[str, str] = {
                name: agents[name].description or ""
                for name in agent_names[i + 1 :]
                if name in agents
            }
            try:
                handoff_decision = await handoff.evaluate_handoff(
                    current_agent=current_agent_name,
                    work_completed=str(agent_result),
                    remaining_work=remaining_work,
                    available_agents=available_agents_map,
                )
            except Exception as exc:
                logger.warning(
                    "Handoff evaluation failed for %s -> %s: %s",
                    current_agent_name,
                    next_agent_name,
                    exc,
                )
                handoff_decision = None

            # Create handoff package if recommended
            if handoff_decision == next_agent_name:
                remaining_objectives = derive_objectives(remaining_work)

                try:
                    handoff_context = await handoff.create_handoff_package(
                        from_agent=current_agent_name,
                        to_agent=next_agent_name,
                        work_completed=str(agent_result),
                        artifacts=artifacts,
                        remaining_objectives=remaining_objectives,
                        task=task,
                        handoff_reason=(
                            f"Sequential workflow: {current_agent_name} completed, "
                            f"passing to {next_agent_name}"
                        ),
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to create handoff package for %s -> %s: %s",
                        current_agent_name,
                        next_agent_name,
                        exc,
                    )
                    handoff_context = None

                # Format handoff as structured input for next agent
                if handoff_context is not None:
                    result = format_handoff_input(handoff_context)
                else:
                    result = str(agent_result)

                if handoff_context is not None:
                    logger.info("✓ Handoff created: %s → %s", current_agent_name, next_agent_name)
                    logger.info("  Estimated effort: %s", handoff_context.estimated_effort)
            else:
                # Simple pass-through (current behavior)
                result = str(agent_result)
        else:
            # Last agent - no handoff needed
            result = str(agent_result)

    return str(result), aggregated_usage


async def execute_sequential_streaming(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    task: str,
    progress_callback: ProgressCallback | None = None,
    *,
    enable_handoffs: bool = False,
    handoff: HandoffManager | None = None,
    thread: AgentThread | None = None,
) -> AsyncIterator[MagenticAgentMessageEvent | WorkflowOutputEvent]:
    """Execute task sequentially through agents with streaming."""

    if not agent_names:
        raise AgentExecutionError(
            agent_name="unknown",
            task="sequential execution",
            original_error=RuntimeError("Sequential execution requires at least one agent"),
        )

    result = task
    total_agents = len([name for name in agent_names if name in agents])
    current_agent_idx = 0
    artifacts: dict[str, Any] = {}
    agent_trace: list[dict[str, Any]] = []
    handoff_history: list[dict[str, Any]] = []

    for step_index, agent_name in enumerate(agent_names):
        agent = _get_agent(agents, agent_name)
        if not agent:
            yield create_system_event(
                stage="execution",
                event="agent.skipped",
                text=f"Skipping unknown agent '{agent_name}'",
                payload={"agent": agent_name},
            )
            continue

        current_agent_idx += 1
        if progress_callback:
            progress_callback.on_progress(
                f"Executing {agent_name} ({current_agent_idx}/{total_agents})...",
                current=current_agent_idx,
                total=total_agents,
            )

        yield create_agent_event(
            stage="execution",
            event="agent.start",
            agent=agent_name,
            text=f"{agent_name} starting sequential step",
            payload={
                "position": current_agent_idx,
                "total_agents": total_agents,
            },
        )

        try:
            if thread is None:
                response = await agent.run(result)
            else:
                response = await agent.run(result, thread=thread)
        except Exception as exc:
            if progress_callback:
                progress_callback.on_error(f"{agent_name} failed", exc)
            yield create_agent_event(
                stage="execution",
                event="agent.error",
                agent=agent_name,
                text=f"{agent_name} failed sequential step",
                payload={"error": str(exc)},
            )
            agent_trace.append(
                {
                    "agent": agent_name,
                    "error": str(exc),
                }
            )
            # Preserve prior result and continue to the next agent.
            continue
        result_text = str(response)
        artifacts.update(extract_artifacts(result_text))

        yield create_agent_event(
            stage="execution",
            event="agent.output",
            agent=agent_name,
            text=result_text,
            payload={
                "output": result_text,
                "artifacts": list(artifacts.keys()),
            },
        )

        yield create_agent_event(
            stage="execution",
            event="agent.completed",
            agent=agent_name,
            text=f"{agent_name} completed sequential step",
            payload={
                "result_preview": result_text[:200],
                "artifacts": list(artifacts.keys()),
            },
        )

        agent_trace.append(
            {
                "agent": agent_name,
                "output_preview": result_text[:200],
                "artifacts": list(artifacts.keys()),
            }
        )

        # Handoff handling (only before final agent)
        if enable_handoffs and handoff and step_index < len(agent_names) - 1:
            next_agent_name = agent_names[step_index + 1]
            try:
                remaining_work = estimate_remaining_work(task, result_text)
                available_agents = {
                    name: getattr(agents[name], "description", name)
                    for name in agent_names[step_index + 1 :]
                    if name in agents
                }

                if available_agents:
                    next_agent = await handoff.evaluate_handoff(
                        current_agent=agent_name,
                        work_completed=result_text,
                        remaining_work=remaining_work,
                        available_agents=available_agents,
                    )

                    if next_agent == next_agent_name:
                        remaining_objectives = derive_objectives(remaining_work)
                        handoff_context = await handoff.create_handoff_package(
                            from_agent=agent_name,
                            to_agent=next_agent_name,
                            work_completed=result_text,
                            artifacts=artifacts,
                            remaining_objectives=remaining_objectives,
                            task=task,
                            handoff_reason=(
                                f"Sequential workflow handoff {agent_name} → {next_agent_name}"
                            ),
                        )

                        handoff_history.append(handoff_context.to_dict())
                        yield create_system_event(
                            stage="handoff",
                            event="handoff.created",
                            text=f"Handoff {agent_name} → {next_agent_name}",
                            payload={"handoff": handoff_context.to_dict()},
                            agent=f"{agent_name}->{next_agent_name}",
                        )

                        formatted_input = format_handoff_input(handoff_context)
                        result = formatted_input
                        continue
            except Exception as exc:
                yield create_system_event(
                    stage="handoff",
                    event="handoff.error",
                    text=f"Handoff failed for {agent_name} → {next_agent_name}",
                    payload={"error": str(exc)},
                    agent=f"{agent_name}->{next_agent_name}",
                )

        result = result_text

    final_payload = {
        "agent_executions": agent_trace,
        "handoff_history": handoff_history,
        "artifacts": artifacts,
    }

    yield create_system_event(
        stage="execution",
        event="agent.summary",
        text="Sequential execution complete",
        payload={"agents": agent_names},
    )

    msg = ChatMessage(role=Role.ASSISTANT, text=result, additional_properties=final_payload)
    yield WorkflowOutputEvent(
        data=[msg],
        source_executor_id="sequential_execution",
    )
