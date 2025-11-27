"""Execution strategies for the workflow.

Consolidated from former execution/ module.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from agent_framework._agents import ChatAgent
from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import MagenticAgentMessageEvent, WorkflowOutputEvent

from ..utils.logger import setup_logger
from ..utils.models import ExecutionMode, RoutingDecision
from .exceptions import AgentExecutionError
from .group_chat_builder import GroupChatBuilder
from .handoff import HandoffContext, HandoffManager
from .helpers import (
    derive_objectives,
    estimate_remaining_work,
    extract_artifacts,
    synthesize_results,
)
from .models import ExecutionOutcome

if TYPE_CHECKING:
    from ..utils.progress import ProgressCallback
    from .context import SupervisorContext

logger = setup_logger(__name__)


def _get_agent(agents: dict[str, ChatAgent], name: str) -> ChatAgent | None:
    """Get agent from map with case-insensitive lookup."""
    if name in agents:
        return agents[name]

    # Try case-insensitive match
    name_lower = name.lower()
    if name_lower in agents:
        return agents[name_lower]

    # Try stripping "Agent" suffix (e.g. "ResearcherAgent" -> "researcher")
    if name.endswith("Agent"):
        short_name = name[:-5].lower()
        if short_name in agents:
            return agents[short_name]

    # Try finding key that matches case-insensitive
    for key, agent in agents.items():
        if key.lower() == name_lower:
            return agent

    # Agent lookup failed - log available agents for debugging
    logger.warning(f"Agent lookup failed for '{name}'. Available keys: {list(agents.keys())}")
    return None


def _extract_tool_usage(response: Any) -> list[dict[str, Any]]:
    """Extract tool usage metadata from an agent response."""
    usage = []
    if hasattr(response, "messages"):
        for msg in response.messages:
            # Check for tool calls in the message (standard ChatMessage structure)
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    usage.append(
                        {
                            "tool": tool_call.get("name", "unknown"),
                            "arguments": tool_call.get("arguments", {}),
                            "timestamp": getattr(msg, "timestamp", None),
                        }
                    )
            # Check for tool usage in additional_properties (DSPy/custom agents)
            if hasattr(msg, "additional_properties"):
                props = msg.additional_properties
                if "tool_usage" in props:
                    usage.extend(props["tool_usage"])

    # Check top-level additional_properties if response itself has them
    if hasattr(response, "additional_properties"):
        props = response.additional_properties
        if props and "tool_usage" in props:
            usage.extend(props["tool_usage"])

    return usage


# --- Execution Phase Helper ---


class ExecutionPhaseError(RuntimeError):
    """Raised when execution phase prerequisites are not satisfied."""


async def run_execution_phase(
    *,
    routing: RoutingDecision,
    task: str,
    context: SupervisorContext,
) -> ExecutionOutcome:
    """Execute task according to the routing decision and return structured outcome."""
    agents_map = context.agents
    if not agents_map:
        raise ExecutionPhaseError("Agents must be initialized before execution phase runs.")

    assigned_agents: list[str] = list(routing.assigned_to)
    subtasks: list[str] = list(routing.subtasks)
    tool_usage: list[dict[str, Any]] = []

    if routing.mode is ExecutionMode.PARALLEL:
        result, usage = await execute_parallel(agents_map, assigned_agents, subtasks)
        tool_usage.extend(usage)
    elif routing.mode is ExecutionMode.SEQUENTIAL:
        result, usage = await _execute_sequential_helper(
            agents_map=agents_map,
            agents=assigned_agents,
            task=task,
            enable_handoffs=context.enable_handoffs,
            handoff_manager=context.handoff,
        )
        tool_usage.extend(usage)
    else:
        delegate = assigned_agents[0] if assigned_agents else None
        if delegate is None:
            raise ExecutionPhaseError("Delegated execution requires at least one assigned agent.")
        result, usage = await execute_delegated(agents_map, delegate, task)
        tool_usage.extend(usage)

    logger.info(f"Execution result: {str(result)[:200]}...")
    logger.info(f"Execution tool usage: {len(tool_usage)} items")

    return ExecutionOutcome(
        result=str(result),
        mode=routing.mode,
        assigned_agents=assigned_agents,
        subtasks=subtasks,
        status="success",
        artifacts={},
        tool_usage=tool_usage,
    )


async def run_execution_phase_streaming(
    *,
    routing: RoutingDecision,
    task: str,
    context: SupervisorContext,
):
    """Execute task with streaming events."""
    agents_map = context.agents
    if not agents_map:
        raise ExecutionPhaseError("Agents must be initialized before execution phase runs.")

    assigned_agents: list[str] = list(routing.assigned_to)
    subtasks: list[str] = list(routing.subtasks)

    # We will accumulate usage and result to return a final outcome if needed,
    # but primarily we yield events.
    # Since this is a generator, we can't 'return' the outcome easily.
    # We will yield the events, and the caller will have to reconstruct the outcome
    # or we yield a special final event.
    # For now, let's yield events and then yield the ExecutionOutcome at the end.

    if routing.mode is ExecutionMode.PARALLEL:
        async for event in execute_parallel_streaming(agents_map, assigned_agents, subtasks):
            if isinstance(event, MagenticAgentMessageEvent):
                yield event
            elif isinstance(event, WorkflowOutputEvent):
                # This contains the result
                yield event

    elif routing.mode is ExecutionMode.SEQUENTIAL:
        async for event in execute_sequential_streaming(
            agents_map,
            assigned_agents,
            task,
            enable_handoffs=context.enable_handoffs,
            handoff=context.handoff,
        ):
            if isinstance(event, (MagenticAgentMessageEvent, WorkflowOutputEvent)):
                yield event

    elif routing.mode is ExecutionMode.DISCUSSION or routing.mode == "discussion":
        async for event in execute_discussion_streaming(
            agents_map,
            assigned_agents,
            task,
            reasoner=context.dspy_supervisor,
            progress_callback=context.progress_callback,
        ):
            if isinstance(event, (MagenticAgentMessageEvent, WorkflowOutputEvent)):
                yield event

    else:
        delegate = assigned_agents[0] if assigned_agents else None
        if delegate is None:
            raise ExecutionPhaseError("Delegated execution requires at least one assigned agent.")
        async for event in execute_delegated_streaming(agents_map, delegate, task):
            if isinstance(event, (MagenticAgentMessageEvent, WorkflowOutputEvent)):
                yield event


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


# --- Streaming Event Helpers ---


def create_agent_event(
    *,
    stage: str,
    event: str,
    agent: str,
    text: str,
    payload: dict[str, Any] | None = None,
) -> MagenticAgentMessageEvent:
    """Build a structured MagenticAgentMessageEvent for agent activity."""
    message = ChatMessage(role=Role.ASSISTANT, text=text)

    # Attach metadata to the event object dynamically
    evt = MagenticAgentMessageEvent(agent_id=agent, message=message)
    evt.stage = stage  # type: ignore[attr-defined]
    evt.event = event  # type: ignore[attr-defined]
    evt.payload = dict(payload or {})  # type: ignore[attr-defined]
    return evt


def create_system_event(
    *,
    stage: str,
    event: str,
    text: str,
    payload: dict[str, Any] | None = None,
    agent: str | None = None,
) -> MagenticAgentMessageEvent:
    """Build a structured event for non-agent/system updates."""
    message = ChatMessage(role=Role.ASSISTANT, text=text)

    evt = MagenticAgentMessageEvent(agent_id=agent or "System", message=message)
    evt.stage = stage  # type: ignore[attr-defined]
    evt.event = event  # type: ignore[attr-defined]
    evt.payload = dict(payload or {})  # type: ignore[attr-defined]
    return evt


# --- Execution Strategies ---


async def execute_delegated(
    agents: dict[str, ChatAgent],
    agent_name: str,
    task: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Delegate the task to a single agent without streaming."""
    agent = _get_agent(agents, agent_name)
    if not agent:
        raise AgentExecutionError(
            agent_name=agent_name,
            task=task,
            original_error=RuntimeError(f"Agent '{agent_name}' not found"),
        )

    response = await agent.run(task)
    usage = _extract_tool_usage(response)
    return str(response), usage


async def execute_delegated_streaming(
    agents: dict[str, ChatAgent],
    agent_name: str,
    task: str,
    progress_callback: ProgressCallback | None = None,
):
    """Delegate task to single agent with streaming."""
    if agent_name not in agents:
        raise AgentExecutionError(
            agent_name=agent_name,
            task=task,
            original_error=RuntimeError(f"Agent '{agent_name}' not found"),
        )

    if progress_callback:
        progress_callback.on_progress(f"Executing {agent_name}...")
    yield create_agent_event(
        stage="execution",
        event="agent.start",
        agent=agent_name,
        text=f"{agent_name} started delegated execution",
        payload={"task_preview": task[:120]},
    )

    response = await agents[agent_name].run(task)

    if progress_callback:
        progress_callback.on_progress(f"{agent_name} completed")
    result_text = str(response)
    yield create_agent_event(
        stage="execution",
        event="agent.completed",
        agent=agent_name,
        text=f"{agent_name} completed delegated execution",
        payload={"result_preview": result_text[:200]},
    )

    # Yield final result
    metadata = {"agent": agent_name}
    msg = ChatMessage(role=Role.ASSISTANT, text=result_text, additional_properties=metadata)
    summary_event = WorkflowOutputEvent(
        data=[msg],
        source_executor_id="delegated_execution",
    )
    yield create_system_event(
        stage="execution",
        event="agent.summary",
        text=f"{agent_name} result ready",
        payload={"agent": agent_name},
    )
    yield summary_event


async def execute_parallel(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    subtasks: list[str],
) -> tuple[str, list[dict[str, Any]]]:
    """Execute subtasks in parallel without streaming."""
    tasks = []
    valid_agent_names = []

    for agent_name, subtask in zip(agent_names, subtasks, strict=False):
        agent = _get_agent(agents, agent_name)
        if not agent:
            logger.warning("Skipping unknown agent '%s' during parallel execution", agent_name)
            continue
        tasks.append(agent.run(subtask))
        valid_agent_names.append(agent_name)

    if not tasks:
        raise AgentExecutionError(
            agent_name="unknown",
            task="parallel execution",
            original_error=RuntimeError("No valid agents available"),
        )

    # Execute with exception handling
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and handle exceptions
    successful_results = []
    aggregated_usage = []

    for agent_name, result in zip(valid_agent_names, results, strict=False):
        if isinstance(result, Exception):
            logger.error(f"Agent '{agent_name}' failed: {result}")
            successful_results.append(f"[{agent_name} failed: {result!s}]")
        else:
            successful_results.append(str(result))
            aggregated_usage.extend(_extract_tool_usage(result))

    return synthesize_results(successful_results), aggregated_usage


async def execute_parallel_streaming(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    subtasks: list[str],
    progress_callback: ProgressCallback | None = None,
):
    """Execute subtasks in parallel with streaming."""
    tasks = []
    valid_agent_names = []
    valid_subtasks = []
    for agent_name, subtask in zip(agent_names, subtasks, strict=False):
        agent = _get_agent(agents, agent_name)
        if agent:
            tasks.append(agent.run(subtask))
            valid_agent_names.append(agent_name)
            valid_subtasks.append(subtask)

    if progress_callback:
        progress_callback.on_progress(
            f"Executing {len(valid_agent_names)} agents in parallel...",
            current=0,
            total=len(valid_agent_names),
        )

    # Yield start events for each agent
    for agent_name, subtask in zip(valid_agent_names, valid_subtasks, strict=False):
        yield create_agent_event(
            stage="execution",
            event="agent.start",
            agent=agent_name,
            text=f"{agent_name} starting parallel subtask",
            payload={"subtask": subtask},
        )

    # Execute with exception handling
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Yield completion events and handle exceptions
    successful_results = []
    for idx, (agent_name, result) in enumerate(zip(valid_agent_names, results, strict=False), 1):
        if progress_callback:
            progress_callback.on_progress(
                f"Agent {agent_name} completed", current=idx, total=len(valid_agent_names)
            )
        if isinstance(result, Exception):
            logger.error(f"Agent '{agent_name}' failed: {result}")
            error_msg = f"[{agent_name} failed: {result!s}]"
            yield create_agent_event(
                stage="execution",
                event="agent.error",
                agent=agent_name,
                text=f"{agent_name} failed during parallel execution",
                payload={"error": str(result)},
            )
            successful_results.append(error_msg)
        else:
            result_text = str(result)
            yield create_agent_event(
                stage="execution",
                event="agent.completed",
                agent=agent_name,
                text=f"{agent_name} completed parallel subtask",
                payload={"result_preview": result_text[:200]},
            )
            successful_results.append(result_text)

    # Yield final synthesized result
    final_result = synthesize_results(successful_results)
    yield create_system_event(
        stage="execution",
        event="agent.summary",
        text="Parallel execution complete",
        payload={"agents": valid_agent_names},
    )

    metadata = {"agents": valid_agent_names}
    msg = ChatMessage(role=Role.ASSISTANT, text=final_result, additional_properties=metadata)
    yield WorkflowOutputEvent(
        data=[msg],
        source_executor_id="parallel_execution",
    )


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
        return await execute_sequential_with_handoffs(agents, agent_names, task, handoff)

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
        if simple_mode:
            # Pass result directly without string conversion
            response = await agent.run(result)
        else:
            response = await agent.run(str(result))

        aggregated_usage.extend(_extract_tool_usage(response))
        result = str(response)

    return str(result), aggregated_usage


async def execute_sequential_with_handoffs(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    task: str,
    handoff: HandoffManager,
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
        agent_result = await agent.run(str(result))
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
            handoff_decision = await handoff.evaluate_handoff(
                current_agent=current_agent_name,
                work_completed=str(agent_result),
                remaining_work=remaining_work,
                available_agents=available_agents_map,
            )

            # Create handoff package if recommended
            if handoff_decision == next_agent_name:
                remaining_objectives = derive_objectives(remaining_work)

                handoff_context = await handoff.create_handoff_package(
                    from_agent=current_agent_name,
                    to_agent=next_agent_name,
                    work_completed=str(agent_result),
                    artifacts=artifacts,
                    remaining_objectives=remaining_objectives,
                    task=task,
                    handoff_reason=f"Sequential workflow: {current_agent_name} completed, passing to {next_agent_name}",
                )

                # Format handoff as structured input for next agent
                result = format_handoff_input(handoff_context)

                logger.info(f"✓ Handoff created: {current_agent_name} → {next_agent_name}")
                logger.info(f"  Estimated effort: {handoff_context.estimated_effort}")
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
):
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

        response = await agent.run(result)
        result_text = str(response)
        artifacts.update(extract_artifacts(result_text))

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
                        handoff_reason=f"Sequential workflow handoff {agent_name} → {next_agent_name}",
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


async def execute_discussion_streaming(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    task: str,
    reasoner: Any,  # DSPyReasoner
    progress_callback: ProgressCallback | None = None,
):
    """Execute task via group chat discussion."""

    if not agent_names:
        raise AgentExecutionError(
            agent_name="unknown",
            task="discussion execution",
            original_error=RuntimeError("Discussion execution requires at least one agent"),
        )

    # Build group chat manager
    builder = GroupChatBuilder()
    for name in agent_names:
        agent = _get_agent(agents, name)
        if agent:
            builder.add_agent(agent)

    if reasoner:
        builder.set_reasoner(reasoner)

    manager = builder.build()

    if progress_callback:
        progress_callback.on_progress("Starting group discussion...")

    yield create_system_event(
        stage="execution",
        event="discussion.start",
        text="Starting group discussion",
        payload={"participants": agent_names},
    )

    # Run chat
    history = await manager.run_chat(initial_message=task)

    # Yield events for each message in history (except the first user message)
    for msg in history[1:]:
        yield create_agent_event(
            stage="execution",
            event="agent.message",
            agent=getattr(msg, "name", "unknown"),
            text=msg.text,
            payload={"role": msg.role},
        )

    yield create_system_event(
        stage="execution",
        event="discussion.completed",
        text="Group discussion completed",
        payload={"rounds": len(history)},
    )

    # Yield final result (last message content)
    if history:
        last_msg = history[-1]
        yield WorkflowOutputEvent(
            data=[last_msg],
            source_executor_id="discussion_execution",
        )
