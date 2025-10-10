"""
AgenticFleet Workflows Package
==============================

This package contains workflow coordination logic for the AgenticFleet system.

Workflows:
    - magentic_workflow: Multi-agent coordination using Magentic pattern

The Magentic workflow pattern enables:
- Dynamic agent participation and coordination
- Event-driven observability and monitoring
- Configurable execution limits and safety controls
- State management across agent interactions

Usage:
    from workflows.magentic_workflow import create_magentic_workflow

    # Create and execute workflow
    workflow = create_magentic_workflow()
    result = await workflow.run("Your task here")
"""

from workflows.magentic_workflow import create_magentic_workflow

__all__ = ["create_magentic_workflow"]
