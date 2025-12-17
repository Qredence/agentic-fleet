"""AgenticFleet API package.

This package provides the FastAPI router aggregation layer,
following the FastAPI full-stack template structure.

Structure:
    api/
    ├── __init__.py      # This file - package exports
    ├── main.py          # Router aggregation
    ├── deps.py          # Dependency injection
    └── routes/          # Endpoint modules
        ├── chat.py      # WebSocket streaming
        ├── workflows.py # Workflow execution & history
        ├── conversations.py
        └── agents.py
"""

from .deps import (
    ConversationManagerDep,
    SessionManagerDep,
    SettingsDep,
    WorkflowDep,
    get_conversation_manager,
    get_session_manager,
    get_workflow,
)
from .main import api_router

__all__ = [
    # Dependencies
    "ConversationManagerDep",
    "SessionManagerDep",
    "SettingsDep",
    "WorkflowDep",
    # Router
    "api_router",
    "get_conversation_manager",
    "get_session_manager",
    "get_workflow",
]
