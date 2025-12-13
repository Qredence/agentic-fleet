"""API route modules.

Each module provides endpoints for a specific domain:
- chat: WebSocket streaming for real-time chat
- workflows: Workflow execution (/run)
- sessions: Workflow session management (/sessions)
- history: Execution history (/history)
- dspy: DSPy introspection (/dspy/*)
- nlu: Intent/entity endpoints (/classify_intent, /extract_entities)
- conversations: Conversation CRUD operations
- agents: Agent listing and information
"""

from . import agents, chat, conversations, dspy, history, nlu, optimize, sessions, workflows

__all__ = [
    "agents",
    "chat",
    "conversations",
    "dspy",
    "history",
    "nlu",
    "optimize",
    "sessions",
    "workflows",
]
