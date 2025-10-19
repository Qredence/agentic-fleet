# Testing Guide: /v1/workflow/reflection API

This guide provides instructions for testing the workflow reflection API endpoint.

## Prerequisites

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync --all-extras

# Or using pip
pip install -e ".[dev]"
```

### 2. Configure Environment

Create `.env` file with OpenAI credentials:

```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o  # or your preferred model
```

## Running Tests

### Unit Tests

```bash
# Test entity catalog
uv run pytest tests/test_workflow_as_agent_api.py -v

# Test HTTP endpoint (requires server running)
uv run pytest tests/test_reflection_endpoint.py -v

# Run all tests
uv run pytest -v
```

### Manual Testing

#### 1. Start the Backend Server

Terminal 1:
```bash
make haxui-server

# Or directly:
uv run uvicorn agenticfleet.haxui.api:app --reload --port 8000
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Initializing FleetRuntime...
INFO:     Magentic Fleet registered (lazy)
INFO:     Workflow as Agent registered (lazy)
INFO:     FleetRuntime initialized
INFO:     HaxUI API started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 2. Health Check

```bash
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "healthy",
  "version": "0.5.3",
  "agents_dir": null
}
```

#### 3. Entity Discovery

```bash
curl http://localhost:8000/v1/entities
```

Expected (truncated):
```json
{
  "entities": [
    {
      "id": "researcher",
      "type": "agent",
      "name": "Researcher Agent",
      ...
    },
    {
      "id": "magentic_fleet",
      "type": "workflow",
      "name": "Magentic Fleet Orchestration",
      ...
    },
    {
      "id": "workflow_as_agent",
      "type": "workflow",
      "name": "Reflection Workflow (Worker + Reviewer)",
      ...
    }
  ]
}
```

#### 4. Test Reflection Endpoint

```bash
curl -X POST http://localhost:8000/v1/workflow/reflection \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is 2+2? Be concise.",
    "worker_model": "gpt-4.1-nano",
    "reviewer_model": "gpt-4.1"
  }' \
  --no-buffer
```

Expected (SSE stream):
```
data: {"type":"response.output_text.delta","delta":"Worker:...","item_id":"msg_..."}

data: {"type":"response.output_text.delta","delta":"Generating...","item_id":"msg_..."}

data: {"type":"response.done","conversation_id":"conv_...","message_id":"msg_..."}

data: [DONE]
```

#### 5. Test with Python Client

```bash
uv run python examples/test_reflection_api.py
```

Expected output:
```
======================================================================
Testing Reflection Workflow Endpoint
======================================================================

Endpoint: http://localhost:8000/v1/workflow/reflection
Query: Explain quantum entanglement in simple terms.
Worker Model: gpt-4.1-nano
Reviewer Model: gpt-4.1

----------------------------------------------------------------------
Streaming response...
----------------------------------------------------------------------

[Streamed response text appears here...]

----------------------------------------------------------------------
Response completed
Conversation ID: conv_abc123
Message ID: msg_abc123_reflection
Usage: {'input_tokens': 8, 'output_tokens': 120, 'total_tokens': 128}

======================================================================
Total events: 15
Response length: 500 characters
======================================================================
```

## Test Scenarios

### Scenario 1: Basic Query

```bash
curl -X POST http://localhost:8000/v1/workflow/reflection \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Python?"}'
```

**Expected**: SSE stream with Worker/Reviewer interaction, final approved response.

### Scenario 2: Custom Models

```bash
curl -X POST http://localhost:8000/v1/workflow/reflection \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain machine learning",
    "worker_model": "gpt-4o-mini",
    "reviewer_model": "gpt-4o"
  }'
```

**Expected**: Uses specified models for Worker and Reviewer.

### Scenario 3: Conversation Persistence

```bash
# Create conversation
CONV_ID=$(curl -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.id')

# Use conversation
curl -X POST http://localhost:8000/v1/workflow/reflection \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Hello\", \"conversation_id\": \"$CONV_ID\"}"

# Get conversation history
curl http://localhost:8000/v1/conversations/$CONV_ID/items
```

**Expected**: Messages stored in conversation, retrievable later.

### Scenario 4: Missing Query (Error Handling)

```bash
curl -X POST http://localhost:8000/v1/workflow/reflection \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected**:
```json
{
  "detail": "Missing or invalid 'query' field."
}
```
HTTP Status: 400

### Scenario 5: Invalid Conversation ID

```bash
curl -X POST http://localhost:8000/v1/workflow/reflection \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Test",
    "conversation_id": "invalid_id"
  }'
```

**Expected**:
```json
{
  "detail": "Conversation not found."
}
```
HTTP Status: 404

## Integration Tests

### Test Suite Structure

```
tests/
├── test_workflow_as_agent_api.py  # Runtime and catalog tests
├── test_reflection_endpoint.py     # HTTP endpoint tests
├── conftest.py                     # Test fixtures
└── ...
```

### Running Specific Tests

```bash
# Test entity catalog
uv run pytest tests/test_workflow_as_agent_api.py::test_workflow_as_agent_in_catalog -v

# Test catalog structure
uv run pytest tests/test_workflow_as_agent_api.py::test_entity_catalog_structure -v

# Test runtime initialization
uv run pytest tests/test_workflow_as_agent_api.py::test_runtime_initialization -v

# Test HTTP endpoint (requires server)
uv run pytest tests/test_reflection_endpoint.py::test_reflection_workflow_endpoint -v
```

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Server Logs

Server logs show:
- Runtime initialization
- Entity registration
- Workflow agent creation
- SSE event streaming
- Errors and warnings

### Common Issues

#### 1. Connection Refused

**Problem**: `curl: (7) Failed to connect to localhost port 8000`

**Solution**: Ensure backend is running (`make haxui-server`)

#### 2. Missing Dependencies

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Install dependencies (`uv sync`)

#### 3. OpenAI API Error

**Problem**: `openai.error.AuthenticationError`

**Solution**: Set `OPENAI_API_KEY` in `.env`

#### 4. Timeout

**Problem**: Request times out

**Solution**: Increase timeout in client:
```python
httpx.AsyncClient(timeout=120.0)
```

## Performance Testing

### Load Test with curl

```bash
# Run 10 concurrent requests
for i in {1..10}; do
  curl -X POST http://localhost:8000/v1/workflow/reflection \
    -H "Content-Type: application/json" \
    -d '{"query": "Test '$i'"}' \
    --no-buffer &
done
wait
```

### Benchmark Response Times

```python
import time
import httpx

async def benchmark():
    start = time.time()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/workflow/reflection",
            json={"query": "Test"}
        )
    elapsed = time.time() - start
    print(f"Response time: {elapsed:.2f}s")
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Install dependencies
  run: uv sync --all-extras

- name: Run unit tests
  run: uv run pytest tests/test_workflow_as_agent_api.py -v

- name: Start backend
  run: uv run uvicorn agenticfleet.haxui.api:app --port 8000 &

- name: Wait for server
  run: sleep 5

- name: Run integration tests
  run: uv run pytest tests/test_reflection_endpoint.py -v
```

## Monitoring

### Metrics to Track

- Response time (time to first byte)
- Stream completion time
- Worker/Reviewer iteration count
- Token usage
- Error rate
- Concurrent connection count

### Health Check Integration

Add to monitoring tools:
```bash
# Check every 30 seconds
*/30 * * * * curl -f http://localhost:8000/health || alert
```

## Next Steps

1. ✅ Basic endpoint working
2. ⏳ Add authentication/authorization
3. ⏳ Add rate limiting
4. ⏳ Add request validation middleware
5. ⏳ Add observability (OpenTelemetry)
6. ⏳ Add caching layer
7. ⏳ Deploy to production

## Resources

- API Documentation: `docs/api/reflection-endpoint.md`
- Implementation Details: `docs/api/IMPLEMENTATION.md`
- Example Client: `examples/test_reflection_api.py`
- Source Code: `src/agenticfleet/haxui/api.py`
