"""Typed DSPy decision modules for Phase 1 refactor.

This package contains independently-loadable DSPy modules for specific decision tasks:
- Routing: Task routing and agent assignment
- Tool Planning: Tool selection and planning
- Quality: Answer quality assessment

Each module uses typed signatures with Pydantic output models (DSPy >= 3.0.3)
for reliable structured outputs.
"""

from .quality import QualityDecisionModule, get_quality_module
from .routing import RoutingDecisionModule, get_routing_module
from .tool_planning import ToolPlanningModule, get_tool_planning_module

__all__ = [
    "QualityDecisionModule",
    "RoutingDecisionModule",
    "ToolPlanningModule",
    "get_quality_module",
    "get_routing_module",
    "get_tool_planning_module",
]
