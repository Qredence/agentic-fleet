# API Integration Guide

This document explains how the frontend API integration works and how to troubleshoot issues.

## Architecture Overview

The frontend communicates with the backend through:

1. **REST API endpoints** - For creating sessions, conversations, approvals
2. **Server-Sent Events (SSE)** - For real-time streaming of workflow execution

## API Endpoints

### Backend Endpoints

| Endpoint                         | Method | Purpose                | Frontend Usage             |
| -------------------------------- | ------ | ---------------------- | -------------------------- |
| `/health`                        | GET    | Health check           | Connection status          |
| `/v1/sessions`                   | POST   | Create session         | `createSession()`          |
| `/v1/sessions/{id}/chat`         | POST   | Start chat execution   | `createChatExecution()`    |
| `/v1/chat/stream/{execution_id}` | GET    | SSE stream events      | SSE connection             |
| `/v1/conversations`              | POST   | Create conversation    | `createConversation()`     |
| `/v1/conversations`              | GET    | List conversations     | `getConversations()`       |
| `/v1/conversations/{id}/items`   | GET    | Get conversation items | Conversation history       |
| `/v1/approvals`                  | GET    | List approvals         | `listApprovals()`          |
| `/v1/approvals/{id}`             | POST   | Respond to approval    | `submitApprovalDecision()` |

### Frontend API Client

Located in `src/frontend/src/lib/api/`:

- `client.ts` - Base API request function with error handling
- `chat.ts` - Session and chat execution endpoints
- `conversations.ts` - Conversation management
- `approvals.ts` - Approval workflows
- `health.ts` - Health check endpoint
- `api-config.ts` - API URL configuration

## Data Flow

### 1. Sending a Message

```
Frontend (useFastAPIChat hook)
  ↓
1. createConversation() → POST /v1/conversations
  ↓
2. createSession() → POST /v1/sessions
  ↓
3. createChatExecution() → POST /v1/sessions/{id}/chat
  ↓
4. Connect to SSE → GET /v1/chat/stream/{execution_id}
  ↓
5. Parse SSE events → Update UI state
```

### 2. SSE Event Streaming

The backend streams events via SSE:

- `connection` - Initial connection event
- `delta` - Streaming text chunks from agents
- `agent_message` - Complete agent response
- `orchestrator_message` - Manager coordination messages
- `workflow.completed` - Workflow finished
- `error` - Error occurred
- `heartbeat` - Keep-alive signal

### 3. Event Processing

Frontend processes events in `use-fastapi-chat.ts`:

- `handleSSEEvent()` - Routes events to appropriate handlers
- Type guards (`isSseAgentDeltaEvent`, etc.) - Validate event types
- State updates - Updates messages, plans, approvals

## Configuration

### Backend URL

Set via environment variable or default:

```bash
# .env file
VITE_BACKEND_URL=http://localhost:8000
```

Or defaults to `http://localhost:8000` in `api-config.ts`.

### CORS

Backend CORS is configured in `src/agenticfleet/core/settings.py`:

```python
cors_origins: list[str] = ["*"]  # Allow all in development
```

For production, restrict to specific origins:

```python
cors_origins: list[str] = ["https://yourdomain.com"]
```

### Vite Proxy

During development, Vite proxies requests:

```typescript
// vite.config.ts
proxy: {
  "/v1": {
    target: "http://localhost:8000",
    changeOrigin: true,
  },
  "/health": {
    target: "http://localhost:8000",
    changeOrigin: true,
  },
}
```

## Troubleshooting

### 1. API Requests Failing

**Symptoms**: Network errors, 404s, CORS errors

**Solutions**:

- Verify backend is running: `curl http://localhost:8000/health`
- Check CORS configuration in `settings.py`
- Verify frontend URL matches backend expectations
- Check browser console for specific error messages

### 2. SSE Not Connecting

**Symptoms**: No streaming, connection errors

**Solutions**:

- Verify execution was created: Check `/v1/sessions/{id}/chat` response
- Check execution_id is correct
- Verify SSE endpoint: `/v1/chat/stream/{execution_id}`
- Check browser network tab for SSE connection
- Verify event_collector exists in backend state

### 3. Messages Not Appearing

**Symptoms**: API succeeds but UI doesn't update

**Solutions**:

- Check browser console for JavaScript errors
- Verify SSE events are being received (network tab)
- Check event parsing in `useSSEEventParser.ts`
- Verify message state updates in React DevTools

### 4. Session Creation Fails

**Symptoms**: "Session not found" or workflow creation errors

**Solutions**:

- Verify workflow factory initialization: `state.workflow_factory`
- Check YAML config exists: `src/agenticfleet/magentic_fleet.yaml`
- Verify workflow factory functions exist in `workflow.py`
- Check backend logs for workflow creation errors

## Testing

### Manual API Testing

Use the test script:

```bash
uv run python scripts/test-api-endpoints.py
```

Or test manually:

```bash
# Health check
curl http://localhost:8000/health

# Create session
curl -X POST http://localhost:8000/v1/sessions

# Create conversation
curl -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Frontend Testing

1. Open browser DevTools (F12)
2. Go to Network tab
3. Filter by "Fetch/XHR"
4. Send a message in the UI
5. Verify:
   - POST `/v1/conversations` - 201 Created
   - POST `/v1/sessions` - 200 OK
   - POST `/v1/sessions/{id}/chat` - 200 OK
   - GET `/v1/chat/stream/{execution_id}` - 200 OK (SSE)

### Debugging Tips

1. **Enable verbose logging**:

   ```python
   # Backend
   LOGGER.setLevel(logging.DEBUG)
   ```

2. **Check browser console**:
   - Look for `[Dedup]` messages (message deduplication)
   - Look for `[WebSocket]` messages (if using WebSocket)
   - Check for API errors

3. **Verify backend state**:
   - Check `state.chat_sessions` - should have session
   - Check `state.event_collectors` - should have execution_id
   - Check `state.workflow_factory` - should be initialized

4. **Network inspection**:
   - Use browser DevTools Network tab
   - Check request/response headers
   - Verify SSE events are streaming

## Common Issues

### Issue: CORS errors

**Error**: `Access-Control-Allow-Origin` header missing

**Fix**: Ensure CORS middleware is configured in `server.py` and `cors_origins` includes your frontend URL.

### Issue: SSE connection fails immediately

**Error**: `Execution {id} not found`

**Fix**: Ensure chat execution was created before connecting to SSE stream. Check execution_id matches.

### Issue: No events streamed

**Problem**: SSE connects but no events received

**Fix**:

- Verify workflow execution started: Check backend logs
- Verify event_collector exists: `state.event_collectors.get(execution_id)`
- Check workflow factory created workflow correctly

### Issue: Workflow creation fails

**Error**: `Failed to create workflow instance`

**Fix**:

- Verify YAML config exists: `src/agenticfleet/magentic_fleet.yaml`
- Check workflow factory function exists: `create_magentic_fleet_workflow`
- Verify OpenAI API key is set: `OPENAI_API_KEY`

## Production Checklist

- [ ] Set specific CORS origins (not `["*"]`)
- [ ] Configure proper backend URL via environment variable
- [ ] Enable HTTPS for production
- [ ] Set up proper error logging
- [ ] Configure rate limiting
- [ ] Set up monitoring/alerting
- [ ] Test SSE streaming over production network
- [ ] Verify WebSocket connections (if used)

## Additional Resources

- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [Server-Sent Events MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Frontend API Client Code](./src/frontend/src/lib/api/client.ts)
- [Backend Routes](./src/agenticfleet/api/routes/)
