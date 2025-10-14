"""
Magentic Fleet module for Microsoft Agent Framework-based orchestration.

This module provides a Magentic workflow implementation that uses:
- StandardMagenticManager for planning and progress evaluation
- MagenticOrchestratorExecutor for coordination
- MagenticAgentExecutor wrappers for specialist agents

The fleet dynamically orchestrates researcher, coder, and analyst agents
based on planner decisions rather than manual DELEGATE token parsing.
"""

from agenticfleet.fleet.magentic_fleet import MagenticFleet, create_default_fleet

__all__ = ["MagenticFleet", "create_default_fleet"]
