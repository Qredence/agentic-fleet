"""Sequential execution strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework import WorkflowOutputEvent

from ...utils.logger import setup_logger
from ..exceptions import AgentExecutionError
from ..handoff_manager import HandoffContext, HandoffManager
from ..utils import derive_objectives, estimate_remaining_work, extract_artifacts
from .streaming_events import create_agent_event, create_system_event

if TYPE_CHECKING:
    from ...utils.progress import ProgressCallback

logger = setup_logger(__name__)


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
    agents: dict[str, Any],
    agent_names: list[str],
    task: str,
    enable_handoffs: bool = False,
    handoff_manager: HandoffManager | None = None,
    *,
    simple_mode: bool | None = None,
) -> str:
    """Execute a task sequentially across agents without streaming."""
    if not agent_names:
        raise AgentExecutionError(
            agent_name="unknown",
            task="sequential execution",
            original_error=RuntimeError("Sequential execution requires at least one agent"),
        )

    # Use handoff-enabled execution if available
    if enable_handoffs and handoff_manager:
        return await execute_sequential_with_handoffs(agents, agent_names, task, handoff_manager)

    # Standard sequential execution (original behavior)
    result: Any = task
    for agent_name in agent_names:
        agent = agents.get(agent_name)
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
            result = await agent.run(result)
        else:
            result = await agent.run(str(result))

    return str(result)


async def execute_sequential_with_handoffs(
    agents: dict[str, Any],
    agent_names: list[str],
    task: str,
    handoff_manager: HandoffManager,
) -> str:
    """Execute sequential workflow with intelligent handoffs.

    This method uses the HandoffManager to create structured handoffs
    between agents with rich context, artifacts, and quality criteria.
    """
    result = task
    artifacts: dict[str, Any] = {}

    for i, current_agent_name in enumerate(agent_names):
        agent = agents.get(current_agent_name)
        if not agent:
            logger.warning(f"Skipping unknown agent '{current_agent_name}'")
            continue

        # Execute current agent's work
        logger.info(f"Agent {current_agent_name} starting work")
        agent_result = await agent.run(str(result))

        # Extract artifacts from result (simplified - could be more sophisticated)
        current_artifacts = extract_artifacts(agent_result)
        artifacts.update(current_artifacts)

        # Check if handoff is needed (before last agent)
        if i < len(agent_names) - 1:
            next_agent_name = agent_names[i + 1]
            remaining_work = estimate_remaining_work(task, str(agent_result))

            # Evaluate if handoff should proceed
            handoff_decision = await handoff_manager.evaluate_handoff(
                current_agent=current_agent_name,
                work_completed=str(agent_result),
                remaining_work=remaining_work,
                available_agents={
                    name: agents[name].description
                    for name in agent_names[i + 1 :]
                    if name in agents
                },
            )

            # Create handoff package if recommended
            if handoff_decision == next_agent_name:
                remaining_objectives = derive_objectives(remaining_work)

                handoff_context = await handoff_manager.create_handoff_package(
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

    return str(result)


async def execute_sequential_streaming(
    agents: dict[str, Any],
    agent_names: list[str],
    task: str,
    progress_callback: ProgressCallback | None = None,
    *,
    enable_handoffs: bool = False,
    handoff_manager: HandoffManager | None = None,
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
        agent = agents.get(agent_name)
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
        if enable_handoffs and handoff_manager and step_index < len(agent_names) - 1:
            next_agent_name = agent_names[step_index + 1]
            remaining_work = estimate_remaining_work(task, result_text)
            available_agents = {
                name: getattr(agents[name], "description", name)
                for name in agent_names[step_index + 1 :]
                if name in agents
            }

            if available_agents:
                next_agent = await handoff_manager.evaluate_handoff(
                    current_agent=agent_name,
                    work_completed=result_text,
                    remaining_work=remaining_work,
                    available_agents=available_agents,
                )

                if next_agent == next_agent_name:
                    remaining_objectives = derive_objectives(remaining_work)
                    handoff_context = await handoff_manager.create_handoff_package(
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
        "result": result,
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
    yield WorkflowOutputEvent(
        data=final_payload,
        source_executor_id="sequential_execution",
    )
