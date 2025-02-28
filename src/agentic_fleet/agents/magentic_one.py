"""
MagenticOne agent implementation for AgenticFleet.

This module provides a wrapper and configuration for the MagenticOne agent from autogen.
"""

from typing import Any, Dict, List, Optional, Union

from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.teams.magentic_one import MagenticOne as AutogenMagenticOne


class MagenticOneAgent:
    """MagenticOne agent implementation for AgenticFleet.

    This class provides a wrapper around the MagenticOne agent from autogen,
    with additional configuration and integration with the AgenticFleet framework.
    """

    def __init__(self, client: Any, code_executor: Optional[Any] = None, hil_mode: bool = True, **kwargs: Any):
        """Initialize the MagenticOne agent.

        Args:
            client: The LLM client to use
            code_executor: The code executor to use (defaults to LocalCommandLineCodeExecutor)
            hil_mode: Whether to enable human-in-the-loop mode
            **kwargs: Additional parameters to pass to the MagenticOne constructor
        """
        self.client = client
        self.code_executor = code_executor or LocalCommandLineCodeExecutor()
        self.hil_mode = hil_mode
        self.kwargs = kwargs

        # Initialize the MagenticOne agent
        self.agent = AutogenMagenticOne(
            client=self.client, code_executor=self.code_executor, hil_mode=self.hil_mode, **self.kwargs
        )

    async def run_stream(self, task: str) -> Any:
        """Run the agent on a task and stream the results.

        Args:
            task: The task to run

        Returns:
            An async generator that yields response chunks
        """
        return self.agent.run_stream(task=task)

    async def run(self, task: str) -> Any:
        """Run the agent on a task.

        Args:
            task: The task to run

        Returns:
            The agent's response
        """
        return await self.agent.run(task=task)


def create_magentic_one_agent(
    client: Any, code_executor: Optional[Any] = None, hil_mode: bool = True, **kwargs: Any
) -> MagenticOneAgent:
    """Create a MagenticOne agent.

    Args:
        client: The LLM client to use
        code_executor: The code executor to use (defaults to LocalCommandLineCodeExecutor)
        hil_mode: Whether to enable human-in-the-loop mode
        **kwargs: Additional parameters to pass to the MagenticOne constructor

    Returns:
        A MagenticOneAgent instance
    """
    return MagenticOneAgent(client=client, code_executor=code_executor, hil_mode=hil_mode, **kwargs)
