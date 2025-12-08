"""FastAPI dependency injection and lifespan management.

DEPRECATED: This module is maintained for backward compatibility only.
All dependencies have been reorganized into the dependencies/ directory.

New code should import directly from agentic_fleet.app.dependencies instead.
"""

# Re-export all dependencies from the new dependencies/ directory for backward compatibility
from agentic_fleet.app.dependencies import (
    ConversationManager,
    ConversationManagerDep,
    SessionManagerDep,
    SettingsDep,
    WorkflowDep,
    WorkflowSessionManager,
    get_conversation_manager,
    get_session_manager,
    get_workflow,
    lifespan,
)

__all__ = [
    # Lifespan
    "lifespan",
    "get_conversation_manager",
    "get_session_manager",
    # Managers
    "ConversationManager",
    "WorkflowSessionManager",
    # Injectors
    "WorkflowDep",
    "SessionManagerDep",
    "ConversationManagerDep",
    "SettingsDep",
    "get_workflow",
]
