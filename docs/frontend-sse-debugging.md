# Frontend SSE Debugging Guide

## Problem Statement

The frontend successfully sends requests to the backend (`/v1/responses`) and receives 200 OK responses, but SSE events are not being processed or displayed in the UI. The chat shows "Thinking..." indefinitely with loading spinners.

## What Works ✅

1. **Backend API**: cURL tests work perfectly - instant SSE responses
2. **Network requests**: Frontend successfully creates conversations (201) and sends messages (200)
3. **Request flow**: `sendMessage()` → `ensureConversationId()` → `postAndStream()` all execute
4. **Model routing**: `workflow_as_agent` is correctly identified and routed in runtime.py

## What Doesn't Work ❌

1. **SSE event processing**: `readSSEStream()` function never logs "received chunk" or "flushing line"
2. **UI updates**: Messages never appear, loading state persists indefinitely
3. **Event handler**: `onEvent()` callback in `sendMessage()` is never invoked

## Debug Logging Added

Added comprehensive `console.log()` statements throughout the SSE chain:

### In `postAndStream()`

```typescript
console.log("[DEBUG] postAndStream: sending request", { url, payloadSummary });
console.log("[DEBUG] postAndStream: response status", {
  status,
  ok,
  contentType,
});
console.log(
  "[DEBUG] postAndStream: starting SSE read loop with reader",
  reader
);
console.log("[DEBUG] postAndStream: onEvent function is", typeof onEvent);
console.log("[DEBUG] postAndStream: readSSEStream completed");
```

### In `readSSEStream()`

```typescript
console.log("[DEBUG] readSSEStream: BEGIN");
console.log("[DEBUG] readSSEStream: chunk received", {
  done,
  chunkLength,
  chunkPreview,
});
console.log("[DEBUG] readSSEStream: flushing line", preview);
console.log("[DEBUG] readSSEStream: parsing payload", payload.slice(0, 100));
console.log("[DEBUG] readSSEStream: calling onEvent with", parsed);
console.log("[DEBUG] readSSEStream: END");
```

### In `sendMessage()` event handler

```typescript
console.log("[DEBUG] Received event:", event);
```

## Expected Console Output (If Working)

```
[DEBUG] sendMessage called with: Write a hello world function
[DEBUG] Ensuring conversation ID...
[DEBUG] Conversation ID: conv_abc123
[DEBUG] Starting postAndStream...
[DEBUG] postAndStream: sending request { url: "/v1/responses", ... }
[DEBUG] postAndStream: response status { status: 200, ok: true, contentType: "text/event-stream" }
[DEBUG] postAndStream: starting SSE read loop with reader [object ReadableStreamDefaultReader]
[DEBUG] postAndStream: onEvent function is function
[DEBUG] readSSEStream: BEGIN
[DEBUG] readSSEStream: chunk received { done: false, chunkLength: 156, chunkPreview: "data: {\"type\":..." }
[DEBUG] readSSEStream: flushing line data: {"type":"workflow.event","actor":"worker","text":"..."}
[DEBUG] readSSEStream: parsing payload {"type":"workflow.event","actor":"worker","text":"..."}
[DEBUG] readSSEStream: calling onEvent with { type: "workflow.event", actor: "worker", ... }
[DEBUG] Received event: { type: "workflow.event", actor: "worker", ... }
[DEBUG] readSSEStream: chunk received { done: true }
[DEBUG] readSSEStream: END
[DEBUG] postAndStream: readSSEStream completed
[DEBUG] postAndStream: finished
```

## Actual Console Output (Current Behavior)

```
[DEBUG] sendMessage called with: Write a hello world function
[DEBUG] Ensuring conversation ID...
[DEBUG] Conversation ID: conv_abc123
[DEBUG] Starting postAndStream...
[DEBUG] postAndStream: sending request { ... }
[DEBUG] postAndStream: response status { status: 200, ok: true, ... }
[DEBUG] postAndStream: starting SSE read loop with reader [object ReadableStreamDefaultReader]
[DEBUG] postAndStream: onEvent function is function
[DEBUG] readSSEStream: BEGIN
← **STOPS HERE - No chunk logs, no event processing**
```

## Testing Steps

### 1. Start Backend Server

```bash
cd /Volumes/Samsung-SSD-T7/Workspaces/Github/qredence/agent-framework/v0.5/AgenticFleet
make haxui-server
```

### 2. Test Backend with cURL

```bash
chmod +x test_sse_stream.sh
./test_sse_stream.sh
```

Expected: Should see SSE events streaming in real-time.

### 3. Start Frontend

```bash
cd src/frontend
npm run dev
```

### 4. Open Browser Console

1. Navigate to http://localhost:5173
2. Open DevTools (F12) → Console tab
3. Type a message: "Write a hello world function"
4. Watch console output

### 5. Analyze Console Logs

Look for:

- Does `readSSEStream: BEGIN` appear?
- Does `readSSEStream: chunk received` appear?
- Are chunks empty or contain data?
- Does `readSSEStream: flushing line` appear?
- Does `Received event:` appear?

## Potential Root Causes

### Theory 1: Response Body Not Readable

The `response.body?.getReader()` might be failing silently or returning a reader that never yields data.

**Test**: Add error handling around `reader.read()` calls.

### Theory 2: Content-Type Mismatch

Browser might not be treating response as streamable due to content-type header issues.

**Check**: Network tab → Response Headers → `Content-Type: text/event-stream`

### Theory 3: CORS or Proxy Issues

Vite proxy might be buffering the response instead of streaming it.

**Check**: `vite.config.ts` proxy configuration for streaming support.

### Theory 4: React StrictMode Interference

While we removed the `isMountedRef` check after `ensureConversationId()`, there might be other state issues.

**Test**: Disable StrictMode in `main.tsx` temporarily.

### Theory 5: Fetch API Stream Reading

Modern browsers require specific ReadableStream handling. The `getReader()` API might need different configuration.

**Test**: Try alternative stream reading approach with `response.body.pipeThrough()`.

## Next Actions

1. **Run the frontend** with DevTools open and observe console logs
2. **Compare console output** with expected behavior above
3. **Check Network tab** for response headers and timing
4. **Test with StrictMode disabled** if issue persists
5. **Try alternative streaming approach** if reader.read() never yields data

## Files Modified

- `/src/frontend/src/lib/use-fastapi-chat.ts` - Added comprehensive debug logging
  - `postAndStream()` function (lines ~450-495)
  - `readSSEStream()` function (lines ~63-135)
  - `sendMessage()` event handler (line ~555)

## References

- Backend SSE format: `src/agenticfleet/haxui/api.py:format_sse()` (line 558)
- Workflow routing: `src/agenticfleet/haxui/runtime.py:generate_response()` (line 117)
- Reflection endpoint: `src/agenticfleet/haxui/api.py:/v1/workflow/reflection` (line 145)
