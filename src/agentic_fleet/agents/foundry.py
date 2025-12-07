"""Adapter for Azure AI Foundry Agents.

This module allows remote agents hosted in Azure AI Foundry (Project Foundry)
to be used transparently within the AgenticFleet, adhering to the standard
ChatAgent interface.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable
from typing import TYPE_CHECKING, Any, cast

from agent_framework._agents import ChatAgent
from agent_framework._types import AgentRunResponse, AgentRunResponseUpdate, ChatMessage, Role

from ..utils.logger import setup_logger
from ..utils.telemetry import optional_span

if TYPE_CHECKING:
    from agent_framework._threads import AgentThread
    from azure.ai.projects.aio import AIProjectClient

logger = setup_logger(__name__)


class FoundryAgentAdapter(ChatAgent):
    """Adapter that proxies a local ChatAgent to an Azure AI Foundry Agent.

    This class handles the lifecycle of interacting with a remote agent:
    1. Creating a thread (if one doesn't exist).
    2. Posting the user's message.
    3. Creating a run.
    4. Polling for completion (or streaming).
    5. Retrieving and formatting the response.
    """

    def __init__(
        self,
        name: str,
        project_client: AIProjectClient,
        agent_id: str,
        description: str = "",
        instructions: str = "",
        poll_interval: float = 1.0,
        cleanup_thread: bool = False,
        tool_names: list[str] | None = None,
        capabilities: list[str] | None = None,
    ) -> None:
        """Initialize the Foundry Agent Adapter.

        Args:
            name: The name of the agent (used for routing).
            project_client: An initialized (async) AIProjectClient connected to the project.
            agent_id: The ID of the agent (Assistant) in Foundry.
            description: Description of the agent's capabilities for the Router.
            instructions: Optional instructions (informational only; Foundry agents use server-side instructions).
            poll_interval: Seconds to wait between poll attempts for run completion.
            cleanup_thread: Whether to delete the thread after execution (stateless mode).
            tool_names: List of tool names available to this agent (informational/routing).
            capabilities: List of high-level capabilities (informational/routing).
        """
        placeholder_chat_client = cast(Any, object())
        super().__init__(
            chat_client=placeholder_chat_client,
            name=name,
            description=description,
            instructions=instructions,
        )
        self.project_client = project_client
        self.agent_id = agent_id
        self.poll_interval = poll_interval
        self.cleanup_thread = cleanup_thread
        self.tool_names = tool_names or []
        self.capabilities = capabilities or []

    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **_kwargs: Any,
    ) -> AgentRunResponse:
        """Execute the remote agent run.

        Args:
            messages: The input message(s).
            thread: Optional thread context. If provided, tries to use an existing Foundry thread ID
                    stored in `thread.additional_properties`.

        Returns:
            The agent's response.
        """
        with optional_span(
            "FoundryAgent.run", attributes={"agent.name": self.name, "agent.id": self.agent_id}
        ):
            # 1. Resolve Text Input
            input_text = self._normalize_input(messages)
            if not input_text:
                return AgentRunResponse(messages=[])

            agents_client = cast(Any, getattr(self.project_client, "agents", None))
            if agents_client is None:
                logger.error("Project client is missing 'agents' interface; cannot create runs")
                return AgentRunResponse(
                    messages=[
                        ChatMessage(
                            role=Role.ASSISTANT,
                            text="Error: Project client is missing agents interface.",
                        )
                    ]
                )

            # 2. Manage Thread
            # Check if our wrapping 'thread' object has a foundry_thread_id
            foundry_thread_id = None
            additional_props = getattr(thread, "additional_properties", None)
            if isinstance(additional_props, dict):
                foundry_thread_id = additional_props.get("foundry_thread_id")

            if not foundry_thread_id:
                # Create new thread on Foundry
                try:
                    remote_thread = await agents_client.create_thread()
                    foundry_thread_id = remote_thread.id
                    # Store it back if possible
                    if isinstance(additional_props, dict):
                        additional_props["foundry_thread_id"] = foundry_thread_id
                    logger.debug(f"Created new Foundry thread: {foundry_thread_id}")
                except Exception as e:
                    logger.error(f"Failed to create Foundry thread: {e}")
                    raise

            try:
                # 3. Add Message
                await agents_client.create_message(
                    thread_id=foundry_thread_id,
                    role="user",
                    content=input_text,
                )

                # 4. Create and Monitor Run
                run = await agents_client.create_run(
                    thread_id=foundry_thread_id,
                    assistant_id=self.agent_id,
                    # We can pass additional instructions if needed, but usually the agent is pre-configured
                )

                logger.info(f"Started Foundry run {run.id} for agent {self.name}")

                # Poll
                while run.status in ("queued", "in_progress", "requires_action"):
                    # NOTE: 'requires_action' usually implies local tool execution requirement.
                    # For this adapter, we assume the agent is fully server-side or we'd need
                    # complex callback logic here. For now, we assume server-side tools.
                    if run.status == "requires_action":
                        logger.warning(
                            f"Foundry agent {self.name} requires action (tool calls). "
                            "This adapter currently assumes server-side execution. Cancelling."
                        )
                        await agents_client.cancel_run(thread_id=foundry_thread_id, run_id=run.id)
                        return AgentRunResponse(
                            messages=[
                                ChatMessage(
                                    role=Role.ASSISTANT,
                                    text="Error: Remote agent requested unsupported local tool action.",
                                )
                            ]
                        )

                    await asyncio.sleep(self.poll_interval)
                    run = await agents_client.get_run(thread_id=foundry_thread_id, run_id=run.id)

                if run.status == "failed":
                    logger.error(f"Foundry run failed: {run.last_error}")
                    return AgentRunResponse(
                        messages=[
                            ChatMessage(
                                role=Role.ASSISTANT,
                                text=f"Error: Remote agent failed. {run.last_error}",
                            )
                        ]
                    )

                # 5. Retrieve Messages
                # List messages, take the latest one from assistant
                msgs = await agents_client.list_messages(thread_id=foundry_thread_id)

                # Foundry returns messages in desc order (newest first) by default usually,
                # but let's check the API spec or just grab the run's messages.
                # Simplified: verify the latest message is the answer.

                response_text = ""
                # Iterate through messages to find the one associated with this run
                # or just the newest assistant message.
                for msg in msgs.data:
                    if msg.role == "assistant" and msg.run_id == run.id:
                        # Extract text content
                        for content_part in msg.content:
                            if content_part.type == "text":
                                response_text += content_part.text.value
                        break

                if not response_text:
                    response_text = "No response content found."

                return AgentRunResponse(
                    messages=[ChatMessage(role=Role.ASSISTANT, text=response_text)],
                    additional_properties={
                        "run_id": run.id,
                        "thread_id": foundry_thread_id,
                        "provider": "foundry",
                    },
                )

            except Exception as e:
                logger.error(f"Error during Foundry execution: {e}")
                raise
            finally:
                if self.cleanup_thread and foundry_thread_id:
                    try:
                        await agents_client.delete_thread(foundry_thread_id)
                    except Exception as e:
                        logger.warning(
                            "Failed to delete Foundry thread %s during cleanup: %s",
                            foundry_thread_id,
                            e,
                        )

    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Stream the remote agent response.

        Note: If the underlying client supports streaming, we hook it up here.
        For now, to strictly manage scope, we will buffer and yield once.
        Future Work: Implement true EventSource streaming from Foundry API.
        """
        # Fallback to blocking run -> yield single update
        response = await self.run(messages, thread=thread, **kwargs)
        text = response.messages[0].text if response.messages else ""

        yield AgentRunResponseUpdate(
            text=text,
            messages=response.messages,
            role=Role.ASSISTANT,
            additional_properties=response.additional_properties,
        )

    def _normalize_input(self, messages: Any) -> str:
        """Helper to extract text from various input formats."""
        if isinstance(messages, str):
            return messages
        if isinstance(messages, ChatMessage):
            return messages.text
        if isinstance(messages, list):
            # Join all user messages? Or just take the last one?
            # Standard practice: Concatenate or take last user query.
            # Here let's extract the last message text.
            if not messages:
                return ""
            last = messages[-1]
            return last if isinstance(last, str) else last.text
        return ""
