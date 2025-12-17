"""Service layer for Microsoft Foundry hosted agents.

This module provides a high-level interface for working with agents hosted
on Microsoft Foundry, including Code Interpreter enabled agents.

Example usage:
    ```python
    from agentic_fleet.services.foundry_agents import FoundryAgentService

    async def main():
        service = FoundryAgentService()

        # Run code with the codex-agent
        async for chunk in service.run_code_agent(
            "Create a Python script that generates fibonacci numbers"
        ):
            print(chunk.text, end="", flush=True)

        # Or use a specific agent
        async for chunk in service.run_agent("codex-agent", "Analyze this data..."):
            print(chunk.text, end="", flush=True)
    ```
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterable
from typing import Any

from agent_framework._types import AgentRunResponse, AgentRunResponseUpdate

from ..agents.foundry import FoundryAgentConfig, FoundryHostedAgent
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class FoundryAgentService:
    """High-level service for interacting with Microsoft Foundry hosted agents."""

    def __init__(
        self,
        endpoint: str | None = None,
        credential: Any | None = None,
    ) -> None:
        """Initialize the Foundry Agent Service.

        Args:
            endpoint: Microsoft Foundry project endpoint URL.
                If None, uses AZURE_AI_PROJECT_ENDPOINT env var.
            credential: Azure credential for authentication.
                If None, uses DefaultAzureCredential.
        """
        self.endpoint = endpoint or os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
        self._credential = credential
        self._agents: dict[str, FoundryHostedAgent] = {}

    def get_agent(
        self,
        agent_id: str,
        *,
        description: str = "",
        capabilities: list[str] | None = None,
        timeout: float = 120.0,
        cleanup_files: bool = False,
    ) -> FoundryHostedAgent:
        """Get or create a Foundry hosted agent instance.

        Args:
            agent_id: The agent ID/name in Microsoft Foundry.
            description: Agent description for routing.
            capabilities: List of agent capabilities.
            timeout: Operation timeout in seconds.
            cleanup_files: Whether to cleanup generated files.

        Returns:
            FoundryHostedAgent instance (not yet connected).
        """
        if agent_id not in self._agents:
            config = FoundryAgentConfig(
                agent_id=agent_id,
                endpoint=self.endpoint,
                description=description,
                capabilities=capabilities or [],
                timeout=timeout,
                cleanup_files=cleanup_files,
            )
            self._agents[agent_id] = FoundryHostedAgent(
                config=config,
                credential=self._credential,
            )
        return self._agents[agent_id]

    async def run_agent(
        self,
        agent_id: str,
        query: str,
        **kwargs: Any,
    ) -> AgentRunResponse:
        """Run a Foundry agent and return the complete response.

        Args:
            agent_id: The agent ID/name in Microsoft Foundry.
            query: The user query/prompt.
            **kwargs: Additional arguments passed to get_agent().

        Returns:
            AgentRunResponse with the agent's output.
        """
        agent = self.get_agent(agent_id, **kwargs)
        async with agent:
            return await agent.run(query)

    async def run_agent_stream(
        self,
        agent_id: str,
        query: str,
        **kwargs: Any,
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Stream responses from a Foundry agent.

        Args:
            agent_id: The agent ID/name in Microsoft Foundry.
            query: The user query/prompt.
            **kwargs: Additional arguments passed to get_agent().

        Yields:
            AgentRunResponseUpdate chunks.
        """
        agent = self.get_agent(agent_id, **kwargs)
        async with agent:
            async for chunk in agent.run_stream(query):
                yield chunk

    # Convenience methods for specific agents

    async def run_code_agent(
        self,
        query: str,
        *,
        cleanup_files: bool = False,
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Run the codex-agent for code execution with Code Interpreter.

        This is a convenience method for the portal-configured codex-agent
        which has Code Interpreter enabled.

        Args:
            query: The code execution request or Python code to run.
            cleanup_files: Whether to cleanup generated files after retrieval.

        Yields:
            AgentRunResponseUpdate chunks with text and file information.

        Example:
            ```python
            async for chunk in service.run_code_agent(
                "Create a CSV file with 10 random numbers"
            ):
                print(chunk.text, end="", flush=True)
            ```
        """
        async for chunk in self.run_agent_stream(
            agent_id="codex-agent",
            query=query,
            description="Python code execution with Code Interpreter",
            capabilities=["code_interpreter", "file_generation"],
            cleanup_files=cleanup_files,
        ):
            yield chunk

    async def execute_python(
        self,
        code: str,
        *,
        cleanup_files: bool = True,
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Execute Python code using the codex-agent.

        Args:
            code: Python code to execute.
            cleanup_files: Whether to cleanup generated files.

        Yields:
            AgentRunResponseUpdate chunks with execution output.

        Example:
            ```python
            code = '''
            import pandas as pd
            df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
            df.to_csv('/mnt/data/output.csv', index=False)
            print("Done!")
            '''
            async for chunk in service.execute_python(code):
                print(chunk.text, end="", flush=True)
            ```
        """
        query = f"Execute this Python code:\n```python\n{code}\n```"
        async for chunk in self.run_code_agent(query, cleanup_files=cleanup_files):
            yield chunk

    async def close(self) -> None:
        """Close all agent connections."""
        for agent in self._agents.values():
            try:
                await agent.close()
            except Exception as e:
                logger.warning(f"Error closing agent: {e}")
        self._agents.clear()

    async def __aenter__(self) -> FoundryAgentService:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()


# Module-level singleton for convenience
_default_service: FoundryAgentService | None = None


def get_foundry_service() -> FoundryAgentService:
    """Get the default Foundry agent service instance.

    Returns:
        FoundryAgentService singleton instance.
    """
    global _default_service
    if _default_service is None:
        _default_service = FoundryAgentService()
    return _default_service


async def run_code_agent(query: str, **kwargs: Any) -> AsyncIterable[AgentRunResponseUpdate]:
    """Convenience function to run the codex-agent.

    Args:
        query: The code execution request.
        **kwargs: Additional arguments.

    Yields:
        AgentRunResponseUpdate chunks.
    """
    service = get_foundry_service()
    async for chunk in service.run_code_agent(query, **kwargs):
        yield chunk
