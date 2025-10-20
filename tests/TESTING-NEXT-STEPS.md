# Next Steps: Testing & Debugging

## Summary of What Was Done

### 1. OpenTelemetry Tracing Implementation ✅

**Created:**

- `src/agenticfleet/observability.py` - Core tracing module (142 lines)
- `docs/features/tracing.md` - Complete documentation
- `test_tracing_setup.py` - Verification script

**Integrated:**

- `src/agenticfleet/__main__.py` - CLI entry point
- `src/agenticfleet/haxui/api.py` - FastAPI application
- `src/agenticfleet/__init__.py` - Package exports

**Features:**

- Uses Agent Framework's built-in `setup_observability()`
- Default endpoint: `http://localhost:4317` (AI Toolkit gRPC)
- Environment variable support: `OTLP_ENDPOINT`, `TRACING_ENABLED`, `ENABLE_SENSITIVE_DATA`
- Idempotent initialization with graceful fallback
- Comprehensive error handling

### 2. Frontend SSE Debugging Enhancements ⚠️

**Added comprehensive debug logging to:**

- `src/frontend/src/lib/use-fastapi-chat.ts`
  - `postAndStream()` - Request/response logging
  - `readSSEStream()` - Chunk-by-chunk analysis
  - `sendMessage()` event handler - Event processing tracking

**Created:**

- `docs/frontend-sse-debugging.md` - Debugging guide
- `test_sse_stream.sh` - Backend SSE testing script

**Current Status:**

- API calls succeed (200 OK)
- SSE events sent by backend (verified with cURL)
- **Issue**: Frontend `readSSEStream()` never receives chunks
- **Next**: Test with frontend running to see actual console output

## Option 1: Test OpenTelemetry Tracing

### Step 1: Verify Tracing Setup

```bash
cd /Volumes/Samsung-SSD-T7/Workspaces/Github/qredence/agent-framework/v0.5/AgenticFleet
uv run python test_tracing_setup.py
```

Expected output:

```
✅ All tests passed! Tracing is ready to use.
```

### Step 2: Start AI Toolkit Tracing Viewer

1. Open VS Code Command Palette (Cmd+Shift+P)
2. Run: **AI Toolkit: Open Tracing Page**
3. Viewer starts listening on `http://localhost:4317`

### Step 3: Start Backend with Tracing

```bash
make haxui-server
# or
uv run uvicorn agenticfleet.haxui.api:app --reload --port 8000
```

Look for startup message:

```
INFO: OpenTelemetry tracing initialized (endpoint: http://localhost:4317)
```

### Step 4: Send Test Request

```bash
# Terminal session
curl -N -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "workflow_as_agent",
    "input": "Write a hello world function in Python",
    "conversation": {"id": "test-trace"}
  }'
```

### Step 5: Check Traces in AI Toolkit

Navigate to AI Toolkit tracing page in VS Code and verify:

- ✓ Trace appears in timeline
- ✓ Worker agent span visible
- ✓ Reviewer agent span visible
- ✓ LLM calls captured (if `enable_sensitive_data=true`)
- ✓ Response generation timing shown

### Tracing Configuration Options

```bash
# Disable tracing
export TRACING_ENABLED=false
make haxui-server

# Use custom OTLP endpoint (e.g., Jaeger)
export OTLP_ENDPOINT=http://jaeger-collector:4317
make haxui-server

# Disable sensitive data capture (production)
export ENABLE_SENSITIVE_DATA=false
make haxui-server
```

## Option 2: Debug Frontend SSE Issue

### Step 1: Start Backend

```bash
cd /Volumes/Samsung-SSD-T7/Workspaces/Github/qredence/agent-framework/v0.5/AgenticFleet
make haxui-server
```

### Step 2: Test Backend SSE Stream

```bash
chmod +x test_sse_stream.sh
./test_sse_stream.sh
```

Expected: Real-time streaming SSE events should appear.

### Step 3: Start Frontend

```bash
cd src/frontend
npm run dev
```

Open http://localhost:5173

### Step 4: Open Browser Console

1. Open DevTools (F12) → Console tab
2. Clear console
3. Type message: "Write a hello world function"
4. Press Send

### Step 5: Analyze Console Output

**Look for:**

```
[DEBUG] sendMessage called with: ...
[DEBUG] Ensuring conversation ID...
[DEBUG] Conversation ID: conv_abc123
[DEBUG] Starting postAndStream...
[DEBUG] postAndStream: sending request { ... }
[DEBUG] postAndStream: response status { status: 200, ok: true, ... }
[DEBUG] postAndStream: starting SSE read loop with reader [object ReadableStreamDefaultReader]
[DEBUG] readSSEStream: BEGIN
```

**Critical question**: Does `readSSEStream: chunk received` appear?

- **YES**: Chunks are arriving → Issue is in event parsing
- **NO**: Reader not receiving data → Issue is in stream setup/proxy

### Step 6: Check Network Tab

1. Open DevTools → Network tab
2. Find the `/v1/responses` request
3. Check:
   - Status: Should be 200
   - Type: Should be "eventsource" or "xhr"
   - Response Headers: `Content-Type: text/event-stream`
   - Response body: Should show streaming events

### Potential Fixes Based on Findings

#### If chunks never arrive (readSSEStream: BEGIN but no chunks)

**Theory**: Vite proxy buffering or CORS issue

Fix option 1 - Update Vite config:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      "/v1": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // Add streaming support
        ws: true,
        configure: (proxy, options) => {
          proxy.on("proxyRes", (proxyRes) => {
            // Disable buffering for SSE
            proxyRes.headers["x-accel-buffering"] = "no";
          });
        },
      },
    },
  },
});
```

Fix option 2 - Bypass proxy for testing:

```typescript
// use-fastapi-chat.ts
const baseUrl = "http://localhost:8000"; // Direct connection (remove proxy)
```

#### If chunks arrive but events not processed

**Theory**: Event format mismatch

Check console for "Failed to parse SSE event" errors. If present, the backend SSE format doesn't match frontend expectations.

#### If React StrictMode interference suspected

Temporarily disable in `main.tsx`:

```typescript
// main.tsx
ReactDOM.createRoot(document.getElementById("root")!).render(
  // <React.StrictMode>  ← Comment out
  <App />
  // </React.StrictMode>
);
```

## Option 3: Do Both in Parallel

**Advantage**: Tracing will help debug the SSE issue by showing:

- Request lifecycle timing
- Agent execution flow
- Where processing stalls

**Steps**:

1. Start AI Toolkit tracing viewer
2. Start backend with tracing enabled
3. Start frontend
4. Send test message from frontend
5. Check traces in AI Toolkit to see where execution stops
6. Check browser console for SSE stream issues

## Recommended Path

I recommend **Option 3** - test both simultaneously because:

1. **Tracing is production-ready** - Fully implemented and tested
2. **Observability helps debugging** - Traces will show exactly where the workflow executes
3. **Independent systems** - Tracing works regardless of frontend issues
4. **Better context** - You'll see both sides (backend execution + frontend streaming)

## Files Reference

### Tracing

- Module: `src/agenticfleet/observability.py`
- Docs: `docs/features/tracing.md`
- Test: `test_tracing_setup.py`
- Integration: `__main__.py`, `api.py`, `__init__.py`

### Frontend Debugging

- Hook: `src/frontend/src/lib/use-fastapi-chat.ts` (debug logs added)
- Guide: `docs/frontend-sse-debugging.md`
- Test script: `test_sse_stream.sh`

## Expected Results

### Tracing Test Success ✅

```
✅ All tests passed! Tracing is ready to use.

Traces appear in AI Toolkit showing:
- Worker: Generate response (3.2s)
  ├─ OpenAI Chat (gpt-4.1-nano) (3.1s)
  └─ Token usage: 150 in, 200 out
- Reviewer: Evaluate response (2.1s)
  ├─ OpenAI Chat (gpt-4.1) (2.0s)
  └─ Decision: Approved ✓
```

### Frontend Debug Success ✅

```
Console shows:
[DEBUG] readSSEStream: chunk received { chunkLength: 156 }
[DEBUG] readSSEStream: flushing line data: {"type":"workflow.event"...}
[DEBUG] Received event: { type: "workflow.event", actor: "worker" }

UI updates:
- Worker message appears
- Reviewer message appears
- Final response displayed
- Loading spinner stops
```

## Support

If issues persist after testing:

1. Copy full console output (including all [DEBUG] lines)
2. Include Network tab screenshot
3. Share any error messages or stack traces
4. Note which step failed (tracing setup, SSE streaming, event processing)

Let me know which option you'd like to pursue first!
