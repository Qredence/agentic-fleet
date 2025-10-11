"""
AgenticFleet Workflows Package
==============================

This package contains workflow coordination logic for the AgenticFleet system.

Workflows:
    - magentic_workflow: Multi-agent coordination using sequential orchestration

The multi-agent workflow enables:
- Sequential agent coordination through an orchestrator
- Task delegation to specialized agents
- Configurable execution limits and safety controls
- State management across agent interactions

Usage:
    from workflows.magentic_workflow import workflow

    # Execute workflow
    result = await workflow.run("Your task here")
"""

from workflows.magentic_workflow import workflow

__all__ = ["workflow"]
