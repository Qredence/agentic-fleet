"""AgenticFleet API dependencies.

Re-exports all dependency injection functions and managers for backward compatibility.
"""

# Lifespan management
# Re-export create_supervisor_workflow for backward compatibility with tests
from agentic_fleet.workflows.supervisor import create_supervisor_workflow

# Dependency injectors
from .injectors import (
    ConversationManagerDep,
    SessionManagerDep,
    SettingsDep,
    WorkflowDep,
    get_workflow,
)
from .lifespan import (
    get_conversation_manager,
    get_session_manager,
    lifespan,
)

# Manager classes
from .managers import ConversationManager, WorkflowSessionManager

__all__ = [
    # Managers
    "ConversationManager",
    "ConversationManagerDep",
    "SessionManagerDep",
    "SettingsDep",
    # Injectors
    "WorkflowDep",
    "WorkflowSessionManager",
    "create_supervisor_workflow",  # For test compatibility
    "get_conversation_manager",
    "get_session_manager",
    "get_workflow",
    # Lifespan
    "lifespan",
]
