"""Advanced reasoning modules for Agentic Fleet.

This module implements specialized DSPy modules for advanced reasoning strategies:
- ReAct: Reason + Act loop for tool use
- Program of Thought (PoT): Code generation for reasoning
"""

from __future__ import annotations

from typing import Any

import dspy


class FleetReAct(dspy.Module):
    """ReAct (Reason + Act) module for autonomous tool usage.

    Configures ReAct with appropriate max_iters to balance between
    thoroughness and latency/cost. Default max_iters=5 provides good
    coverage while preventing infinite loops.

    Args:
        signature: DSPy signature defining input/output format
        tools: List of tools available for the ReAct agent to use
        max_iters: Maximum number of ReAct iterations to prevent infinite loops.
                   Default is 5 to balance thoroughness with latency/cost.
    """

    def __init__(self, signature: Any = None, tools: list[Any] | None = None, max_iters: int = 5):
        super().__init__()
        # Use dspy.ReAct if available, otherwise fallback or implement custom
        # Configure max_iters to prevent infinite loops and control cost
        # Default of 5 iterations balances thoroughness with latency
        self.react = dspy.ReAct(
            signature or "question -> answer", tools=tools or [], max_iters=max_iters
        )
        self.max_iters = max_iters

    def forward(self, question: str, tools: list[Any] | None = None) -> dspy.Prediction:
        """Execute ReAct loop.

        Args:
            question: The question/task to solve
            tools: Optional list of tools to make available (typically set in constructor)

        Returns:
            Prediction with answer and reasoning
        """
        # Pass tools to the react module if provided
        return self.react(question=question, tools=tools)


class FleetPoT(dspy.Module):
    """Program of Thought module for code-based reasoning."""

    def __init__(self, signature: Any = None):
        super().__init__()
        self.pot = dspy.ProgramOfThought(signature or "question -> answer")
        self.last_error: str | None = None

    def forward(self, question: str) -> dspy.Prediction:
        """Execute Program of Thought.

        Args:
            question: The question/task to solve

        Returns:
            Prediction with answer and reasoning (code)
        """
        self.last_error = None
        try:
            result = self.pot(question=question)
        except RuntimeError as exc:
            self.last_error = str(exc)
            raise
        return result
