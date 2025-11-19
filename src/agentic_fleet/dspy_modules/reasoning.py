"""Advanced reasoning modules for Agentic Fleet.

This module implements specialized DSPy modules for advanced reasoning strategies:
- ReAct: Reason + Act loop for tool use
- Program of Thought (PoT): Code generation for reasoning
"""

from __future__ import annotations

from typing import Any

import dspy


class FleetReAct(dspy.Module):
    """ReAct (Reason + Act) module for autonomous tool usage."""

    def __init__(self, signature: Any = None, tools: list[Any] | None = None):
        super().__init__()
        # Use dspy.ReAct if available, otherwise fallback or implement custom
        # For now, we wrap dspy.ReAct
        self.react = dspy.ReAct(signature or "question -> answer", tools=tools or [])

    def forward(self, question: str, tools: list[Any] | None = None) -> dspy.Prediction:
        """Execute ReAct loop.

        Args:
            question: The question/task to solve
            tools: Optional list of tools to make available

        Returns:
            Prediction with answer and reasoning
        """
        # Note: dspy.ReAct typically takes tools in constructor or context
        # Here we assume they are configured or passed via context manager if dynamic
        return self.react(question=question)


class FleetPoT(dspy.Module):
    """Program of Thought module for code-based reasoning."""

    def __init__(self, signature: Any = None):
        super().__init__()
        self.pot = dspy.ProgramOfThought(signature or "question -> answer")

    def forward(self, question: str) -> dspy.Prediction:
        """Execute Program of Thought.

        Args:
            question: The question/task to solve

        Returns:
            Prediction with answer and reasoning (code)
        """
        return self.pot(question=question)
