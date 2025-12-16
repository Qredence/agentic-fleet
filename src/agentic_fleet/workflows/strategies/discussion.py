"""Discussion/group-chat execution strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_framework._agents import ChatAgent
from agent_framework._threads import AgentThread
from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import WorkflowOutputEvent

from ...utils.logger import setup_logger
from ...utils.models import ExecutionMode, RoutingDecision
from ..exceptions import AgentExecutionError
from ..models import MagenticAgentMessageEvent
from .base import _get_agent, create_agent_event, create_system_event
from .group_chat_adapter import GroupChatBuilder

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ...utils.progress import ProgressCallback
    from ..context import SupervisorContext

logger = setup_logger(__name__)


class DiscussionExecutionStrategy:
    """Execute work using group chat discussion."""

    mode = ExecutionMode.DISCUSSION

    async def stream(
        self,
        *,
        routing: RoutingDecision,
        task: str,
        context: SupervisorContext,
    ) -> AsyncIterator[MagenticAgentMessageEvent | WorkflowOutputEvent]:
        """Stream discussion events for the routing decision."""
        agents_map = context.agents or {}
        async for event in execute_discussion_streaming(
            agents_map,
            list(routing.assigned_to),
            task,
            reasoner=context.dspy_supervisor,
            progress_callback=context.progress_callback,
            thread=context.conversation_thread,
        ):
            yield event


async def execute_discussion_streaming(
    agents: dict[str, ChatAgent],
    agent_names: list[str],
    task: str,
    reasoner: Any,  # DSPyReasoner
    progress_callback: ProgressCallback | None = None,
    thread: AgentThread | None = None,  # Reserved for future use
):
    """Execute task via group chat discussion.

    Note: thread parameter is reserved for future use. Group chat currently
    manages its own internal conversation history.
    """

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
    try:
        history = await manager.run_chat(initial_message=task)
    except Exception as exc:
        if progress_callback:
            progress_callback.on_error("Group discussion failed", exc)
        yield create_system_event(
            stage="execution",
            event="discussion.error",
            text="Group discussion failed",
            payload={"error": str(exc)},
        )
        yield WorkflowOutputEvent(
            data=[ChatMessage(role=Role.ASSISTANT, text=f"[discussion failed: {exc!s}]")],
            source_executor_id="discussion_execution",
        )
        return

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
