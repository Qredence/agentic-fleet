"""Workflow-specific DSPy signatures.

This module contains enhanced signatures for the fleet workflow, specifically
targeting routing efficiency and tool planning optimization.
"""

from __future__ import annotations

from typing import Literal

import dspy


class EnhancedTaskRouting(dspy.Signature):
    """Advanced task routing with efficiency and tool-planning awareness.

    Optimizes for latency and token usage by pre-planning tool usage
    and setting execution constraints.
    """

    task: str = dspy.InputField(desc="Task to be routed")
    team_capabilities: str = dspy.InputField(desc="Capabilities of available agents")
    available_tools: str = dspy.InputField(desc="List of available tools")
    current_context: str = dspy.InputField(desc="Execution context")
    handoff_history: str = dspy.InputField(desc="History of agent handoffs")
    workflow_state: str = dspy.InputField(desc="Current state of the workflow")

    assigned_to: list[str] = dspy.OutputField(desc="Agents assigned to the task")
    execution_mode: Literal["delegated", "sequential", "parallel"] = dspy.OutputField(
        desc="Execution mode"
    )
    subtasks: list[str] = dspy.OutputField(desc="Breakdown of subtasks")

    handoff_strategy: str = dspy.OutputField(desc="Strategy for agent handoffs")
    workflow_gates: str = dspy.OutputField(desc="Quality gates and checkpoints")

    # Efficiency and Tool Planning Fields
    tool_plan: list[str] = dspy.OutputField(desc="Ordered list of tools to use")
    tool_goals: str = dspy.OutputField(desc="Specific goals for tool usage")
    latency_budget: str = dspy.OutputField(desc="Estimated time/latency budget")
    reasoning: str = dspy.OutputField(desc="Reasoning for the routing decision")


class WorkflowStrategy(dspy.Signature):
    """Decides the high-level workflow architecture for a task.

    Selects between:
    - 'handoff': For simple, linear, or real-time tasks (Low latency).
    - 'standard': For complex, multi-step, or quality-critical tasks (High robustness).
    - 'fast_path': For trivial queries (Instant).
    """

    task: str = dspy.InputField(desc="The user's request or task")
    complexity_analysis: str = dspy.InputField(desc="Analysis of task complexity")

    workflow_mode: Literal["handoff", "standard", "fast_path"] = dspy.OutputField(
        desc="The optimal workflow architecture"
    )
    reasoning: str = dspy.OutputField(desc="Why this architecture was chosen")
