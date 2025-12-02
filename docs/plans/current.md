# Implementation Plans

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
