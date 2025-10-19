# Quick Reference: What We Did & What to Test

## ✅ Completed: OpenTelemetry Tracing

### What Was Built

- Full tracing module using Agent Framework's observability
- Integration at CLI and FastAPI entry points
- Comprehensive documentation with examples
- Test script for verification

### Test It Now

```bash
# 1. Verify setup
uv run python test_tracing_setup.py

# 2. Start AI Toolkit tracing (VS Code Command Palette)
# "AI Toolkit: Open Tracing Page"

# 3. Run backend
make haxui-server

# 4. Send request
curl -N -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"model":"workflow_as_agent","input":"test","conversation":{"id":"t1"}}'

# 5. Check traces in AI Toolkit
```

## ⚠️ In Progress: Frontend SSE Debugging

### What Was Added

- Comprehensive `console.log()` debugging throughout SSE chain
- Documentation of expected vs actual behavior
- Test script for backend SSE validation

### Test It Now

```bash
# 1. Start backend
make haxui-server

# 2. Test backend works
./test_sse_stream.sh

# 3. Start frontend
cd src/frontend && npm run dev

# 4. Open browser to http://localhost:5173
# 5. Open DevTools Console (F12)
# 6. Send a message
# 7. Watch for [DEBUG] logs

# Expected: readSSEStream: chunk received { ... }
# If missing: Reader not receiving stream data
```

## Debug Logging Added

### Backend → Frontend Flow

```
Backend SSE Output:
  data: {"type":"workflow.event","actor":"worker","text":"..."}
  data: {"type":"response.output_text.delta","delta":"hello"}
  data: [DONE]

Frontend Logging:
  postAndStream() → Sends fetch request
  readSSEStream() → Reads response.body chunks
  onEvent() → Processes each SSE event
  sendMessage() → Updates UI state
```

### Key Debug Points

```typescript
// In use-fastapi-chat.ts

postAndStream():
  [DEBUG] postAndStream: response status { status, ok, contentType }
  [DEBUG] postAndStream: starting SSE read loop with reader

readSSEStream():
  [DEBUG] readSSEStream: BEGIN
  [DEBUG] readSSEStream: chunk received { done, chunkLength, chunkPreview }
  [DEBUG] readSSEStream: flushing line
  [DEBUG] readSSEStream: calling onEvent with { parsed event }
  [DEBUG] readSSEStream: END

sendMessage():
  [DEBUG] Received event: { type, actor, text }
```

## Files Changed

### New Files

- `src/agenticfleet/observability.py` - Tracing module
- `docs/features/tracing.md` - Tracing docs
- `test_tracing_setup.py` - Tracing test
- `docs/frontend-sse-debugging.md` - Debug guide
- `test_sse_stream.sh` - SSE test script
- `TESTING-NEXT-STEPS.md` - This guide

### Modified Files

- `src/agenticfleet/__main__.py` - Added tracing init
- `src/agenticfleet/haxui/api.py` - Added tracing init
- `src/agenticfleet/__init__.py` - Exported tracing functions
- `src/frontend/src/lib/use-fastapi-chat.ts` - Added debug logs

## Quick Commands

```bash
# Test tracing
uv run python test_tracing_setup.py

# Test backend SSE
./test_sse_stream.sh

# Run backend
make haxui-server

# Run frontend
cd src/frontend && npm run dev

# Check all files changed
git status

# View debug documentation
cat docs/frontend-sse-debugging.md
cat docs/features/tracing.md
```

## Expected Console Output (If Working)

### Tracing Test

```
✅ All tests passed! Tracing is ready to use.
```

### Backend SSE Test

```
data: {"type":"workflow.event","actor":"worker","text":"Processing..."}
data: {"type":"response.output_text.delta","delta":"def"}
data: {"type":"response.output_text.delta","delta":" hello_world()"}
data: [DONE]
```

### Frontend Console

```
[DEBUG] sendMessage called with: test
[DEBUG] Conversation ID: conv_123
[DEBUG] postAndStream: response status { status: 200, ok: true }
[DEBUG] readSSEStream: BEGIN
[DEBUG] readSSEStream: chunk received { chunkLength: 156 }
[DEBUG] Received event: { type: "workflow.event" }
← UI updates with message
```

## If Something Doesn't Work

### Tracing Issues

- Check: AI Toolkit installed and tracing page open
- Check: Port 4317 not in use (`lsof -i :4317`)
- Check: `uv run python test_tracing_setup.py` passes
- Try: `export TRACING_ENABLED=false` to disable

### Frontend SSE Issues

1. **Backend works, frontend doesn't**: Vite proxy or CORS issue
2. **No chunks received**: Reader not streaming, check Network tab
3. **Chunks received, no events**: Parsing error, check console for exceptions
4. **Events received, no UI update**: React state issue, check message state

## Recommended Next Step

**Option 1**: Test tracing first (it's ready and independent)

```bash
uv run python test_tracing_setup.py
# Open AI Toolkit tracing page
make haxui-server
# Send test request, check traces
```

**Option 2**: Debug frontend SSE with enhanced logging

```bash
make haxui-server
cd src/frontend && npm run dev
# Open http://localhost:5173, send message, watch console
```

**Option 3**: Do both - tracing helps debug SSE issues!

```bash
# Terminal 1: Backend with tracing
make haxui-server

# Terminal 2: Frontend
cd src/frontend && npm run dev

# Browser: Open DevTools + AI Toolkit tracing
# Send message, observe both traces and console logs
```

---

**Ready to test!** Pick an option and let me know what you see. 🚀
