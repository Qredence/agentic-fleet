"""Sequential execution strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework import ChatMessage, MagenticAgentMessageEvent, Role, WorkflowOutputEvent

from ...utils.logger import setup_logger
from ..exceptions import AgentExecutionError
from ..handoff_manager import HandoffContext, HandoffManager
from ..utils import derive_objectives, estimate_remaining_work, extract_artifacts

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
):
    """Execute task sequentially through agents with streaming."""
    result = task
    total_agents = len([a for a in agent_names if a in agents])
    current_agent = 0
    for agent_name in agent_names:
        if agent_name in agents:
            current_agent += 1
            if progress_callback:
                progress_callback.on_progress(
                    f"Executing {agent_name} ({current_agent}/{total_agents})...",
                    current=current_agent,
                    total=total_agents,
                )
            yield MagenticAgentMessageEvent(
                agent_id=agent_name,
                message=ChatMessage(role=Role.ASSISTANT, text="Processing task..."),
            )

            response = await agents[agent_name].run(result)

            yield MagenticAgentMessageEvent(
                agent_id=agent_name,
                message=ChatMessage(role=Role.ASSISTANT, text=f"Completed: {response!s}"),
            )

            result = str(response)

    # Yield final result
    yield WorkflowOutputEvent(
        data={"result": result},
        source_executor_id="sequential_execution",
    )
