"""AgenticFleet API dependencies.

Re-exports all dependency injection functions and managers for backward compatibility.
"""

# Lifespan management
from .lifespan import (
    get_conversation_manager,
    get_session_manager,
    lifespan,
)

# Manager classes
from .managers import ConversationManager, WorkflowSessionManager

# Dependency injectors
from .injectors import (
    ConversationManagerDep,
    SessionManagerDep,
    SettingsDep,
    WorkflowDep,
    get_workflow,
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
