from __future__ import annotations

from asyncio import Task
from dataclasses import dataclass, field
from typing import Any

from agenticfleet.api.conversation_store import InMemoryConversationStore
from agenticfleet.api.event_translator import EventTranslator
from agenticfleet.api.redis_client import RedisClient
from agenticfleet.api.websocket_manager import ConnectionManager
from agenticfleet.api.workflow_factory import WorkflowFactory


@dataclass(slots=True)
class BackendState:
    """Container for long-lived backend resources.

    The FastAPI application stores a single instance of :class:`BackendState`
    under ``app.state.backend``. Route handlers and background services use the
    shared object to access conversation persistence, workflow factories, Redis
    connectivity, and the websocket manager. Having a dedicated container keeps
    ``app.state`` tidy and simplifies dependency injection.
    """

    background_tasks: set[Task[Any]] = field(default_factory=set)
    conversation_store: InMemoryConversationStore = field(default_factory=InMemoryConversationStore)
    websocket_manager: ConnectionManager = field(default_factory=ConnectionManager)
    workflow_factory: WorkflowFactory = field(default_factory=WorkflowFactory)
    event_translator: EventTranslator = field(default_factory=EventTranslator)
    redis_client: RedisClient | None = None


def get_backend_state(container: Any) -> BackendState:
    """Retrieve the :class:`BackendState` from a FastAPI app or request.

    ``container`` may be a :class:`fastapi.Request`, :class:`fastapi.WebSocket`,
    or :class:`fastapi.FastAPI` instance. The helper normalises access so that
    dependencies and manual lookups can share the same code path.
    """

    if hasattr(container, "app"):
        container = container.app

    try:
        state = container.state.backend  # type: ignore[attr-defined]
    except AttributeError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("Backend state has not been initialised on the app") from exc

    if not isinstance(state, BackendState):  # pragma: no cover - sanity guard
        raise RuntimeError("Unexpected backend state payload")

    return state
