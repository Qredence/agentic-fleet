"""DSPy signatures for dynamic agent instruction generation."""

from __future__ import annotations

import dspy


class AgentInstructionSignature(dspy.Signature):
    """Generate instructions for an agent based on its role and context."""

    role: str = dspy.InputField(desc="The role of the agent (e.g., 'coder', 'researcher')")
    description: str = dspy.InputField(desc="Description of the agent's responsibilities")
    task_context: str = dspy.InputField(desc="Context of the current task or workflow")

    agent_instructions: str = dspy.OutputField(desc="Detailed system instructions for the agent")


class PlannerInstructionSignature(dspy.Signature):
    """Generate specialized instructions for the Planner/Orchestrator agent."""

    available_agents: str = dspy.InputField(desc="List of available agents and their descriptions")
    workflow_goal: str = dspy.InputField(desc="The goal of the current workflow")

    agent_instructions: str = dspy.OutputField(desc="Detailed instructions for the Planner agent")
