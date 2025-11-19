"""Base agent classes for the fleet.

This module defines the base agent classes used throughout the system,
including the DSPy-enhanced agent that integrates with the Agent Framework.
"""

from __future__ import annotations

from typing import Any, Literal

from agent_framework import ChatAgent

from ..dspy_modules.reasoning import FleetPoT, FleetReAct
from ..utils.cache import TTLCache
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class DSPyEnhancedAgent(ChatAgent):
    """Agent that uses DSPy for enhanced reasoning capabilities.

    This agent wraps the standard ChatAgent and injects DSPy-powered
    reasoning strategies (Chain of Thought, ReAct, Program of Thought)
    to improve performance on complex tasks.
    """

    def __init__(
        self,
        *args: Any,
        reasoning_strategy: Literal[
            "chain_of_thought", "react", "program_of_thought"
        ] = "chain_of_thought",
        cache_ttl: int = 3600,
        **kwargs: Any,
    ) -> None:
        """Initialize the DSPy-enhanced agent.

        Args:
            *args: Arguments passed to ChatAgent
            reasoning_strategy: The reasoning strategy to use
            cache_ttl: Time-to-live for cached results in seconds
            **kwargs: Keyword arguments passed to ChatAgent
        """
        super().__init__(*args, **kwargs)
        self.reasoning_strategy = reasoning_strategy
        self.cache = TTLCache(ttl_seconds=cache_ttl)

        # Initialize reasoning modules
        # We pass self.tools assuming ChatAgent exposes it. If not, it will raise AttributeError
        # which we should catch or ensure ChatAgent has tools.
        # For now, we assume it does as it's a standard pattern.
        tools = getattr(self, "tools", [])
        self.react_module = FleetReAct(tools=tools) if reasoning_strategy == "react" else None
        self.pot_module = FleetPoT() if reasoning_strategy == "program_of_thought" else None

    async def run(self, prompt: str) -> str:
        """Execute the agent's logic with the configured reasoning strategy.

        Args:
            prompt: The input prompt/task

        Returns:
            The agent's response
        """
        logger.info(f"Agent {self.name} running with strategy: {self.reasoning_strategy}")

        # Check cache first
        cached_result = self.cache.get(prompt)
        if cached_result:
            logger.info(f"Cache hit for agent {self.name}")
            return cached_result

        try:
            if self.reasoning_strategy == "react" and self.react_module:
                # Use ReAct strategy
                # Note: We pass the agent's tools to the ReAct module
                # For now, we assume tools are compatible or wrapped
                tools = getattr(self, "tools", [])
                result = self.react_module(question=prompt, tools=tools)
                response = getattr(result, "answer", str(result))

            elif self.reasoning_strategy == "program_of_thought" and self.pot_module:
                # Use Program of Thought strategy
                result = self.pot_module(question=prompt)
                response = getattr(result, "answer", str(result))

            else:
                # Default: Chain of Thought (handled by standard ChatAgent or simple DSPy CoT)
                # For now, we delegate to the standard ChatAgent run which uses the LLM directly
                # but we could wrap it in dspy.ChainOfThought if we had a signature for generic chat.
                response = await super().run(prompt)

            # Cache the result
            self.cache.set(prompt, str(response))
            return str(response)

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            # Fallback to standard execution if enhanced strategy fails
            response = await super().run(prompt)
            return str(response)
