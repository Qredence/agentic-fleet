# Implementation Plans

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

#### Backend (`src/agentic_fleet/app/routers/streaming.py`)

- Replaced SSE endpoint with WebSocket endpoint at `/ws/chat`
- Added `cancel_event` parameter for graceful cancellation
- Client sends `ChatRequest` JSON on connection, receives `StreamEvent` JSON messages
- Supports `{type: "cancel"}` message from client

#### Frontend

- **Vite config**: Added `/ws` proxy rule for WebSocket
- **Types**: Extended `StreamEvent` with "connected" | "cancelled", added `WebSocketClientMessage`
- **useChat hook**: Complete rewrite to use `ReconnectingWebSocket`
- **Tests**: Updated to mock WebSocket instead of fetch/SSE

### Files Modified

1. `src/agentic_fleet/app/routers/streaming.py` - WebSocket endpoint
2. `src/frontend/vite.config.ts` - Proxy configuration
3. `src/frontend/src/api/types.ts` - Type definitions
4. `src/frontend/src/hooks/useChat.ts` - Chat hook rewrite
5. `src/frontend/src/lib/reconnectingWebSocket.ts` - Custom reconnecting WebSocket helper
6. `src/frontend/AGENTS.md` - Documentation update

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
