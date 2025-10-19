# Web-Based Human-in-the-Loop Integration

## Overview

This document describes the web-based approval flow integration between the HaxUI backend and frontend, enabling approval prompts to appear in the browser UI instead of the CLI terminal.

## Problem Statement

Previously, when the AgenticFleet backend (HaxUI API) needed approval for operations (like code execution or plan review), the approval prompt appeared in the **terminal where the server was running**, not in the web frontend. This was because:

1. The `FleetRuntime` was using the CLI `approval_handler` from the console UI
2. The SSE streaming in `api.py` only emitted text deltas, not approval events
3. The frontend had approval UI code but never received approval events

## Solution Architecture

### 1. Web Approval Handler (`haxui/web_approval.py`)

Created `WebApprovalHandler` that implements the `ApprovalHandler` interface but works asynchronously with SSE streams:

```python
class WebApprovalHandler(ApprovalHandler):
    """Stores pending approval requests and waits for web client responses."""

    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        # Store request, wait for response from web client
        pending = PendingApprovalRequest(request)
        self._pending[request.request_id] = pending
        response = await pending.wait_for_response(timeout=300.0)
        return response

    async def set_approval_response(self, request_id, decision, modified_code=None):
        # Called by API endpoint when frontend sends approval response
        pending = self._pending.get(request_id)
        pending.set_response(ApprovalResponse(...))
```

**Key features:**

- Stores pending approval requests in-memory
- Uses `asyncio.Future` to block until response received
- Provides `get_pending_requests()` to retrieve current approvals
- 300-second timeout with auto-reject

### 2. Runtime Integration (`haxui/runtime.py`)

Modified `FleetRuntime` to use `WebApprovalHandler` instead of CLI handler:

```python
class FleetRuntime:
    def __init__(self):
        self.approval_handler = WebApprovalHandler()

    async def ensure_initialised(self):
        self._fleet = create_default_fleet(
            console_ui=None,
            approval_handler=self.approval_handler  # Web handler, not CLI
        )
```

### 3. SSE Streaming Updates (`haxui/api.py`)

#### Approval Request Emission

Modified `build_sse_stream()` to poll for pending approvals and emit SSE events:

```python
async def build_sse_stream(...):
    response_task = asyncio.create_task(runtime.generate_response(...))
    emitted_approval_ids = set()

    # Poll loop: check for approvals or task completion
    while not response_task.done():
        pending = runtime.approval_handler.get_pending_requests()
        for approval_req in pending:
            if req_id not in emitted_approval_ids:
                # Emit approval request event
                yield format_sse({
                    "type": "response.function_approval.requested",
                    "request_id": req_id,
                    "function_call": {...},
                    ...
                })
                emitted_approval_ids.add(req_id)
        await asyncio.sleep(0.1)
```

#### Approval Response Handling

Added `extract_approval_response()` helper and modified `/v1/responses` endpoint:

```python
approval_response = extract_approval_response(payload.get("input"))

if approval_response:
    request_id = approval_response["request_id"]
    approved = approval_response["approved"]
    decision = ApprovalDecision.APPROVED if approved else ApprovalDecision.REJECTED

    # Set approval response on the runtime's handler
    await runtime.approval_handler.set_approval_response(request_id, decision)

    # Return acknowledgment event
    yield format_sse({
        "type": "response.function_approval.responded",
        "request_id": request_id,
        "approved": approved,
        ...
    })
```

## Frontend Integration

The frontend already had all the necessary code to handle approval events:

1. **Type definitions** (`types/openai.ts`):

   - `ResponseFunctionApprovalRequestedEvent`
   - `ResponseFunctionApprovalRespondedEvent`
   - `ResponseInputFunctionApprovalParam`

2. **Store** (`stores/haxuiStore.ts`):

   - `pendingApprovals: PendingApproval[]`
   - `setPendingApprovals()`

3. **Event handling** (`agent-view.tsx` line 888):

   ```typescript
   if (openAIEvent.type === "response.function_approval.requested") {
     const approvalEvent =
       openAIEvent as ResponseFunctionApprovalRequestedEvent;
     setPendingApprovals([
       ...pendingApprovals,
       {
         request_id: approvalEvent.request_id,
         function_call: approvalEvent.function_call,
       },
     ]);
   }
   ```

4. **Approval UI** (already implemented, just needed events)

## Event Flow

### 1. User sends message requiring approval

```
Frontend → POST /v1/responses
  { model: "magentic_fleet", input: "hi", ... }
```

### 2. Backend processes, hits approval point

```
FleetRuntime.generate_response()
  → MagenticFleet.run()
    → Manager agent requests plan_review approval
      → WebApprovalHandler.request_approval()
        → Stores pending request
        → Awaits response (blocks here)
```

### 3. Backend SSE stream emits approval event

```
build_sse_stream() poll loop detects pending approval
  → Emits SSE event:
    data: {"type":"response.function_approval.requested","request_id":"abc123",...}
```

### 4. Frontend displays approval UI

```
agent-view.tsx receives event
  → Updates pendingApprovals store
  → UI renders approval dialog with Approve/Reject buttons
```

### 5. User clicks Approve/Reject

```
Frontend → POST /v1/responses
  {
    model: "magentic_fleet",
    input: [{
      type: "message",
      role: "user",
      content: [{
        type: "function_approval_response",
        request_id: "abc123",
        approved: true
      }]
    }],
    conversation: "conv_xyz"
  }
```

### 6. Backend processes approval

```
create_response() detects approval response
  → Calls runtime.approval_handler.set_approval_response()
    → Resolves Future in WebApprovalHandler
      → ApprovalResponse returned to waiting fleet
        → Execution continues!
```

### 7. Backend continues streaming response

```
MagenticFleet completes execution
  → build_sse_stream() emits text chunks
    → Frontend displays agent response
```

## Configuration

Approval behavior is controlled by `config/workflow.yaml`:

```yaml
human_in_the_loop:
  enabled: true
  approval_timeout_seconds: 300
  require_approval_for:
    - code_execution
    - file_operations
    - plan_review # Manager plan review approval
  trusted_operations:
    - web_search
    - data_analysis
```

## Testing

### Manual Test (what you saw in terminal)

1. **Backend**: Start server with `uv run uvicorn agenticfleet.haxui.api:app --reload`
2. **Frontend**: Start with `cd src/frontend && yarn dev`
3. **Trigger approval**:
   - Open browser to frontend
   - Send message: "hi"
   - Manager creates plan, requires approval
4. **Expected behavior**:
   - Approval dialog appears in browser (not terminal!)
   - Click "Approve" or "Reject"
   - Execution continues or stops based on decision

### Before This Fix

```
Terminal output:
============================================================
⚠️  APPROVAL REQUIRED
============================================================
Agent:       magentic_orchestrator
Operation:   plan_review
Approve? (yes/no/edit): █
```

❌ User had to type in terminal, frontend showed nothing

### After This Fix

```
Browser UI:
┌──────────────────────────────────────────────────┐
│ 🔔 Approval Required                             │
│                                                  │
│ Agent: magentic_orchestrator                     │
│ Operation: plan_review                           │
│ Description: Approve or revise plan              │
│                                                  │
│ [ Approve ]  [ Reject ]                          │
└──────────────────────────────────────────────────┘
```

✅ User clicks button in browser, no terminal interaction needed

## Files Modified

1. **New file**: `src/agenticfleet/haxui/web_approval.py` (170 lines)

   - `WebApprovalHandler` class
   - `PendingApprovalRequest` container
   - Helper functions

2. **Modified**: `src/agenticfleet/haxui/runtime.py`

   - Import `WebApprovalHandler`
   - Add `self.approval_handler = WebApprovalHandler()`
   - Pass to `create_default_fleet()`

3. **Modified**: `src/agenticfleet/haxui/api.py`
   - Import `asyncio`, `ApprovalDecision`
   - Add `extract_approval_response()` helper
   - Update `/v1/responses` endpoint to handle approval inputs
   - Rewrite `build_sse_stream()` to poll for approvals and emit events

## Future Enhancements

1. **Approval history**: Store approval decisions for audit trail
2. **Multi-user approvals**: Support multiple concurrent users with isolated approval queues
3. **Approval policies**: Auto-approve based on rules (e.g., trusted operations)
4. **Code modification UI**: Support MODIFIED decision with code editor
5. **WebSocket alternative**: Consider WebSocket for lower-latency approval delivery
6. **Approval notifications**: Sound/visual alerts when approval needed

## Debugging

If approvals still appear in terminal:

- Check `FleetRuntime.__init__()` creates `WebApprovalHandler`
- Verify `create_default_fleet()` receives `approval_handler` param
- Confirm `build_sse_stream()` poll loop is executing (add logging)
- Check frontend event handler in `agent-view.tsx` line 888

If frontend doesn't show approvals:

- Open browser DevTools → Network → event stream
- Look for `response.function_approval.requested` events
- Check Redux DevTools for `pendingApprovals` state updates
- Verify approval UI component is rendered when `pendingApprovals.length > 0`

## References

- Backend approval interface: `src/agenticfleet/core/approval.py`
- CLI approval handler: `src/agenticfleet/core/cli_approval.py`
- Frontend types: `src/frontend/src/types/openai.ts` (line 142)
- Frontend event handling: `src/frontend/src/components/features/agent/agent-view.tsx` (line 888)
- Configuration: `config/workflow.yaml` (human_in_the_loop section)
