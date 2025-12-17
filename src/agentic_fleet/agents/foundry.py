"""Adapter for Azure AI Foundry Agents.

This module allows remote agents hosted in Azure AI Foundry (Microsoft Foundry)
to be used transparently within the AgenticFleet, adhering to the standard
ChatAgent interface.

Supports two patterns:
1. FoundryAgentAdapter - Legacy polling-based adapter using AIProjectClient
2. FoundryHostedAgent - Modern streaming adapter using AzureAIAgentClient (recommended)
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from agent_framework._agents import ChatAgent
from agent_framework._types import (
    AgentRunResponse,
    AgentRunResponseUpdate,
    ChatMessage,
    ChatResponse,
    ChatResponseUpdate,
    HostedFileContent,
    Role,
)
from agent_framework.azure import AzureAIAgentClient

from ..utils.logger import setup_logger
from ..utils.telemetry import optional_span

if TYPE_CHECKING:
    from agent_framework._threads import AgentThread
    from azure.ai.projects.aio import AIProjectClient

logger = setup_logger(__name__)

# File availability delay in seconds.
# Azure file operations (such as uploading or generating files) may not make files immediately
# available for download due to eventual consistency and propagation delays in Azure's storage
# backend. Empirically, a short delay (0.5 seconds) is often sufficient to ensure that files
# are accessible after creation or upload. This value may need to be adjusted if Azure's
# behavior changes or if file availability issues are observed in production.
FILE_AVAILABILITY_DELAY_SECONDS = 0.5


def parse_connection_string_endpoint(raw: str) -> str:
    """Extract a project endpoint URL from a raw env/config value.

    The Foundry/AI Projects endpoint is sometimes provided directly as a URL, and
    sometimes embedded in a semicolon-separated connection string (e.g.
    "Endpoint=https://...;...".

    This helper is intentionally defensive: it returns an empty string for empty
    input, extracts common key names from key/value strings, and falls back to a
    best-effort URL substring search.
    """

    value = (raw or "").strip()
    if not value:
        return ""

    if value.startswith(("https://", "http://")):
        return value

    # Parse semicolon-separated key=value pairs.
    parts = [p.strip() for p in value.split(";") if p.strip()]
    kv: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        kv[key.strip().lower()] = val.strip().strip('"').strip("'")

    for key in ("endpoint", "project_endpoint", "projectendpoint", "url"):
        endpoint = kv.get(key)
        if endpoint:
            return endpoint

    # Fallback: try to locate a URL substring.
    for scheme in ("https://", "http://"):
        idx = value.find(scheme)
        if idx == -1:
            continue
        tail = value[idx:]
        for sep in (";", " ", "\n", "\r", "\t"):
            cut = tail.find(sep)
            if cut != -1:
                tail = tail[:cut]
                break
        return tail.strip().strip('"').strip("'")

    # Last resort: return as-is.
    return value


@dataclass
class FoundryAgentConfig:
    """Configuration for a Foundry-hosted agent."""

    agent_id: str
    """The agent ID/name in Microsoft Foundry (e.g., 'codex-agent')."""

    endpoint: str | None = None
    """Project endpoint URL. If None, uses AZURE_AI_PROJECT_ENDPOINT env var."""

    description: str = ""
    """Agent description for routing purposes."""

    capabilities: list[str] = field(default_factory=list)
    """List of agent capabilities (e.g., ['code_interpreter', 'file_generation'])."""

    timeout: float = 120.0
    """Timeout for agent operations in seconds."""

    cleanup_files: bool = True
    """Whether to cleanup generated files after retrieval."""


class FoundryHostedAgent:
    """Modern adapter for Microsoft Foundry hosted agents using AzureAIAgentClient.

    This class provides streaming support and handles Code Interpreter tool output
    including file generation and retrieval.

    Example:
        ```python
        async with FoundryHostedAgent(
            config=FoundryAgentConfig(agent_id="codex-agent")
        ) as agent:
            async for chunk in agent.run_stream("Create a fibonacci script"):
                print(chunk.text, end="", flush=True)
        ```
    """

    def __init__(
        self,
        config: FoundryAgentConfig,
        credential: Any | None = None,
    ) -> None:
        """Initialize the Foundry Hosted Agent.

        Args:
            config: Agent configuration.
            credential: Azure credential. If None, uses DefaultAzureCredential.
        """
        self.config = config
        self._credential = credential
        self._client: AzureAIAgentClient | None = None
        self._owns_credential = credential is None

    @property
    def endpoint(self) -> str:
        """Get the project endpoint URL."""
        raw = self.config.endpoint or os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
        return parse_connection_string_endpoint(raw)

    async def __aenter__(self) -> FoundryHostedAgent:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Establish connection to the Foundry project."""
        if self._client is not None:
            return

        if not self.endpoint:
            raise ValueError(
                "Foundry endpoint required. Set AZURE_AI_PROJECT_ENDPOINT env var "
                "or pass endpoint in FoundryAgentConfig."
            )

        # Create credential if not provided
        if self._credential is None:
            from azure.identity.aio import DefaultAzureCredential

            self._credential = DefaultAzureCredential()
            self._owns_credential = True

        # Create the Azure AI Agent client pointing at the hosted agent ID.
        self._client = AzureAIAgentClient(
            credential=self._credential,
            project_endpoint=self.endpoint,
            agent_id=self.config.agent_id,
            # Never delete an existing hosted agent (only affects agents created by the client).
            should_cleanup_agent=False,
        )

        logger.info(f"Connected to Foundry agent '{self.config.agent_id}' at {self.endpoint}")

    async def close(self) -> None:
        """Close the connection and cleanup resources."""
        if self._client is not None:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning(f"Error closing Foundry client: {e}")
            finally:
                self._client = None

        if self._owns_credential and self._credential is not None:
            try:
                await self._credential.close()
            except Exception as e:
                logger.debug(f"Error closing credential: {e}")
            finally:
                self._credential = None

    async def run(self, query: str) -> AgentRunResponse:
        """Execute the agent and return the full response.

        Args:
            query: The user query/prompt.

        Returns:
            AgentRunResponse with the agent's output.
        """
        if self._client is None:
            await self.connect()

        assert self._client is not None

        with optional_span(
            "FoundryHostedAgent.run",
            attributes={
                "agent.id": self.config.agent_id,
                "agent.endpoint": self.endpoint,
            },
        ):
            try:
                response: ChatResponse = await self._client.get_response(
                    [ChatMessage(role=Role.USER, text=query)]
                )
                return AgentRunResponse(
                    messages=[ChatMessage(role=Role.ASSISTANT, text=response.text or "")],
                    additional_properties={
                        "provider": "foundry",
                        "agent_id": self.config.agent_id,
                    },
                )
            except Exception as e:
                logger.error(f"Foundry agent execution failed: {e}")
                return AgentRunResponse(
                    messages=[ChatMessage(role=Role.ASSISTANT, text=f"Error: {e}")],
                )

    async def run_stream(
        self,
        query: str,
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Stream the agent response with file handling.

        Args:
            query: The user query/prompt.

        Yields:
            AgentRunResponseUpdate chunks with text and file information.
        """
        if self._client is None:
            await self.connect()

        assert self._client is not None

        file_ids: list[str] = []

        with optional_span(
            "FoundryHostedAgent.run_stream",
            attributes={
                "agent.id": self.config.agent_id,
                "agent.endpoint": self.endpoint,
            },
        ):
            try:
                async for update in self._client.get_streaming_response(
                    [ChatMessage(role=Role.USER, text=query)]
                ):
                    update = cast(ChatResponseUpdate, update)
                    for content in update.contents:
                        if isinstance(content, HostedFileContent):
                            file_ids.append(content.file_id)

                    # Preserve the original content stream, but wrap in AgentRunResponseUpdate
                    # since the rest of AgenticFleet speaks in agent-level updates.
                    yield AgentRunResponseUpdate(
                        contents=update.contents,
                        role=update.role,
                        response_id=update.response_id,
                        message_id=update.message_id,
                        created_at=update.created_at,
                        additional_properties={
                            "provider": "foundry",
                            **(update.additional_properties or {}),
                        },
                        raw_representation=update.raw_representation,
                    )

                # Handle file retrieval after streaming completes
                if file_ids:
                    yield AgentRunResponseUpdate(
                        text=f"\n\n📁 Generated {len(file_ids)} file(s)",
                        role=Role.ASSISTANT,
                        additional_properties={
                            "provider": "foundry",
                            "file_ids": file_ids,
                        },
                    )

                    # Optionally retrieve file metadata
                    for file_id in file_ids:
                        try:
                            await asyncio.sleep(FILE_AVAILABILITY_DELAY_SECONDS)
                            file_info = await self._client.agents_client.files.get(file_id)
                            yield AgentRunResponseUpdate(
                                text=f"\n  • {file_info.filename} ({file_info.bytes} bytes)",
                                role=Role.ASSISTANT,
                                additional_properties={
                                    "provider": "foundry",
                                    "file_id": file_id,
                                    "filename": file_info.filename,
                                    "size": file_info.bytes,
                                },
                            )

                            # Cleanup if configured
                            if self.config.cleanup_files:
                                try:
                                    await self._client.agents_client.files.delete(file_id)
                                    logger.debug(f"Cleaned up file: {file_id}")
                                except Exception as e:
                                    logger.warning(f"Failed to cleanup file {file_id}: {e}")

                        except Exception as e:
                            logger.warning(f"Failed to retrieve file {file_id}: {e}")

            except Exception as e:
                logger.error(f"Foundry agent streaming failed: {e}")
                yield AgentRunResponseUpdate(
                    text=f"\nError: {e}",
                    role=Role.ASSISTANT,
                    additional_properties={"provider": "foundry", "error": str(e)},
                )

    async def retrieve_file(self, file_id: str) -> bytes | None:
        """Retrieve file content by ID.

        Args:
            file_id: The file ID from Code Interpreter output.

        Returns:
            File content as bytes, or None if retrieval failed.
        """
        if self._client is None:
            await self.connect()

        assert self._client is not None

        try:
            stream = await self._client.agents_client.files.get_content(file_id)
            chunks: list[bytes] = []
            async for chunk in stream:
                chunks.append(chunk)
            return b"".join(chunks)
        except Exception as e:
            logger.error(f"Failed to retrieve file content {file_id}: {e}")
            return None


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
