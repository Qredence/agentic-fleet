# Implementation Plans

## Backend Structure Cleanup (FastAPI Convention)

**Status**: Completed
**Date**: 2025-12-12

### Goal

Refactor the AgenticFleet backend from ~90 scattered files to a cleaner ~18-file structure following FastAPI conventions while preserving all functionality.

### Design Approach

Create facade modules that re-export from existing implementation files. This provides:

- Clean import paths for consumers
- Backward compatibility with existing imports
- Gradual migration path for future consolidation

### Phases Completed

#### Phase 1: API Skeleton + Routes (8 files)

- Created `src/agentic_fleet/api/__init__.py` - Package entry point
- Created route modules: `health.py`, `chat.py`, `nlu.py`, `streaming.py`, `sessions.py`, `conversations.py`, `models.py`, `artifacts.py`
- Each module re-exports from existing `app/routers/` implementations

#### Phase 2: Core Infrastructure (3 files)

- Created `src/agentic_fleet/core/__init__.py` - Package entry point
- Created `core/config.py` - Re-exports from `app/settings.py` + `utils/config.py`
- Created `core/logging.py` - Re-exports from `utils/logger.py`, `utils/tracing.py`, `utils/telemetry.py`, `utils/resilience.py`
- Created `core/storage.py` - Re-exports from `app/conversation_store.py`, `utils/history_manager.py`, `utils/cache.py`
- Created `core/middleware.py` - Re-exports chat workflow middleware

#### Phase 3: Services Layer (4 files)

- Created `src/agentic_fleet/services/__init__.py` - Package entry point
- Created `services/dspy_programs.py` - DSPy signatures, modules, typed models
- Created `services/agents.py` - AgentFactory, prompts, adapters
- Created `services/workflows.py` - SupervisorWorkflow, executors, strategies
- Created `services/conversation.py` - ConversationManager, session management

#### Phase 4: Cleanup + Re-exports

- Updated main `agentic_fleet/__init__.py` with clean public API
- Added lazy imports for both new and legacy paths
- Verified all imports working (499 tests passing)

### New Import Patterns

```python
# Clean API (recommended)
from agentic_fleet import AgentFactory, DSPyReasoner, SupervisorWorkflow
from agentic_fleet.core import get_settings, setup_logger, initialize_tracing
from agentic_fleet.services import ConversationManager

# Legacy API (still works)
from agentic_fleet.agents import AgentFactory
from agentic_fleet.dspy_modules import DSPyReasoner
from agentic_fleet.workflows import SupervisorWorkflow
```

### Test Results

- 499 tests passing
- 3 pre-existing failures (resilience/tracing tests)
- No regressions from restructuring

---

## WebSocket Migration for Chat UI

**Status**: Completed
**Date**: 2025-12-19

### Goal

Replace Server-Sent Events (SSE) with WebSocket for bidirectional real-time chat communication.

### Design Decisions

- **Option A**: New WebSocket per message (chosen for simplicity)
- **Conversation context**: Sent in JSON payload on WebSocket open
- **Auto-reconnection**: Custom `reconnectingWebSocket` helper (TypeScript) with exponential backoff

### Changes Made

#### Backend (`src/agentic_fleet/api/routes/chat.py`)

- Replaced SSE endpoint with WebSocket endpoint at `/api/ws/chat`
- Added `cancel_event` parameter for graceful cancellation
- Client sends `ChatRequest` JSON on connection, receives `StreamEvent` JSON messages
- Supports `{type: "cancel"}` message from client

#### Frontend

- **Vite config**: Added `/ws` proxy rule for WebSocket
- **Types**: Extended `StreamEvent` with "connected" | "cancelled", added `WebSocketClientMessage`
- **useChat hook**: Complete rewrite to use `ReconnectingWebSocket`
- **Tests**: Updated to mock WebSocket instead of fetch/SSE

### Files Modified

1. `src/agentic_fleet/api/routes/chat.py` - WebSocket route (`/api/ws/chat`)
2. `src/agentic_fleet/services/chat_websocket.py` - WebSocket service implementation
3. `src/frontend/vite.config.ts` - Proxy configuration
4. `src/frontend/src/api/types.ts` - Type definitions
5. `src/frontend/src/hooks/useChat.ts` - Chat hook rewrite
6. `src/frontend/src/lib/reconnectingWebSocket.ts` - Custom reconnecting WebSocket helper
7. `src/frontend/AGENTS.md` - Documentation update

---

## Wire Frontend to Backend API

**Status**: Completed
**Date**: 2025-11-29

### Goal

Align the frontend client, types, and state management with the existing FastAPI backend, ensuring full support for streaming events and session management.

### Steps

1.  **Update Frontend Types**
    - Modify `src/frontend/src/api/types.ts` to include `agent.start`, `agent.complete`, `agent.output`, and `agent.thought` in `StreamEvent`.
    - Ensure `ConversationStep` can represent these new events.

2.  **Expand API Client**
    - Add `listSessions`, `getSession`, `cancelSession`, and `listAgents` methods to `src/frontend/src/api/client.ts` matching backend endpoints.

3.  **Update Chat Hook**
    - Modify `src/frontend/src/hooks/useChat.ts` to handle `agent.*` SSE events and map them to `ConversationStep` objects.

4.  **Enhance ChatStep Component**
    - Update `src/frontend/src/components/ChatStep.tsx` to add icons and styling for agent-specific steps (start, complete, output).

### Expected Outcome

- Frontend can display rich agent lifecycle events (start, complete, thoughts).
- Frontend API client covers all major backend endpoints.
- Types are consistent between backend and frontend.
