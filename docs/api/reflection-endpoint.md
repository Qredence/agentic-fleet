# Reflection Workflow API Endpoint

## Overview

The `/v1/workflow/reflection` endpoint provides a dedicated FastAPI route for the **workflow_as_agent** reflection pattern. This endpoint creates a Worker-Reviewer workflow that iteratively improves responses through quality feedback loops.

## Endpoint Details

### POST `/v1/workflow/reflection`

**Description**: Execute the reflection workflow with Worker ↔ Reviewer quality assurance cycle.

**Content-Type**: `application/json`

**Response**: Server-Sent Events (SSE) stream

---

## Request Body

```json
{
  "query": "Your question here",
  "worker_model": "gpt-4.1-nano", // optional, default: "gpt-4.1-nano"
  "reviewer_model": "gpt-4.1", // optional, default: "gpt-4.1"
  "conversation_id": "conv_abc123" // optional, auto-created if omitted
}
```

### Parameters

| Field             | Type   | Required | Default        | Description                                   |
| ----------------- | ------ | -------- | -------------- | --------------------------------------------- |
| `query`           | string | ✅ Yes   | -              | User query to process with reflection pattern |
| `worker_model`    | string | ❌ No    | `gpt-4.1-nano` | Model ID for Worker (response generation)     |
| `reviewer_model`  | string | ❌ No    | `gpt-4.1`      | Model ID for Reviewer (quality evaluation)    |
| `conversation_id` | string | ❌ No    | auto-generated | Existing conversation to continue             |

---

## Response Format

The endpoint streams Server-Sent Events (SSE) with the following event types:

### 1. Output Delta Events

```json
{
  "type": "response.output_text.delta",
  "delta": "text chunk",
  "item_id": "msg_abc123",
  "output_index": 0,
  "sequence_number": 1
}
```

### 2. Completion Event

```json
{
  "type": "response.done",
  "conversation_id": "conv_abc123",
  "message_id": "msg_abc123",
  "sequence_number": 10,
  "usage": {
    "input_tokens": 15,
    "output_tokens": 120,
    "total_tokens": 135
  }
}
```

### 3. Error Event

```json
{
  "type": "error",
  "error": {
    "type": "workflow_error",
    "message": "Error description"
  },
  "sequence_number": 5
}
```

---

## Example Usage

### cURL

```bash
curl -X POST http://localhost:8000/v1/workflow/reflection \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain quantum computing",
    "worker_model": "gpt-4.1-nano",
    "reviewer_model": "gpt-4.1"
  }'
```

### Python (httpx)

```python
import httpx

async def run_reflection():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/v1/workflow/reflection",
            json={"query": "What is machine learning?"}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    print(line[6:])  # Remove "data: " prefix
```

### JavaScript (fetch)

```javascript
const response = await fetch("http://localhost:8000/v1/workflow/reflection", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    query: "Explain photosynthesis",
    worker_model: "gpt-4.1-nano",
    reviewer_model: "gpt-4.1",
  }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { value, done } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  console.log(chunk);
}
```

---

## Workflow Behavior

### 1. Initialization

- User submits query
- Conversation created or retrieved
- Worker and Reviewer executors initialized with specified models

### 2. Worker Phase

- Worker generates initial response using `worker_model`
- Response sent to Reviewer for evaluation

### 3. Reviewer Phase

- Reviewer evaluates against 4 criteria:
  - **Relevance**: Addresses the query
  - **Accuracy**: Factually correct
  - **Clarity**: Easy to understand
  - **Completeness**: Covers all aspects
- Provides structured feedback

### 4. Decision

- ✅ **Approved**: Response emitted to client via SSE
- ❌ **Needs Improvement**: Feedback sent to Worker, regenerates

### 5. Iteration

- Continues Worker ↔ Reviewer cycle until approved
- All intermediate steps visible in SSE stream

---

## Error Handling

### 400 Bad Request

```json
{
  "detail": "Missing or invalid 'query' field."
}
```

**Cause**: Missing or empty `query` field in request body

**Solution**: Provide a valid non-empty `query` string

### 404 Not Found

```json
{
  "detail": "Conversation not found."
}
```

**Cause**: Specified `conversation_id` does not exist

**Solution**: Omit `conversation_id` to auto-create or use valid ID

### 500 Internal Server Error

Streamed as error event:

```json
{
  "type": "error",
  "error": {
    "type": "workflow_error",
    "message": "Detailed error message"
  }
}
```

**Cause**: Workflow execution failure (LLM error, timeout, etc.)

**Solution**: Check logs, verify API keys, retry with simpler query

---

## Advantages Over Generic `/v1/responses`

| Feature                              | `/v1/workflow/reflection` | `/v1/responses` |
| ------------------------------------ | ------------------------- | --------------- |
| **Dedicated for reflection pattern** | ✅ Yes                    | ❌ No           |
| **Explicit Worker/Reviewer models**  | ✅ Yes                    | ❌ No           |
| **Quality assurance built-in**       | ✅ Yes                    | ❌ No           |
| **Simpler request format**           | ✅ Yes                    | ❌ No           |
| **Optimized for iteration**          | ✅ Yes                    | ❌ No           |
| **Conversation persistence**         | ✅ Yes                    | ✅ Yes          |
| **SSE streaming**                    | ✅ Yes                    | ✅ Yes          |

---

## Testing

### Unit Tests

```bash
uv run pytest tests/test_reflection_endpoint.py -v
```

### Integration Test

```bash
uv run python examples/test_reflection_api.py
```

### Manual Test

```bash
# Terminal 1: Start backend
make haxui-server

# Terminal 2: Test endpoint
curl -X POST http://localhost:8000/v1/workflow/reflection \
  -H "Content-Type: application/json" \
  -d '{"query": "What is 2+2?"}'
```

---

## Performance Considerations

### Model Selection

- **Worker (`gpt-4.1-nano`)**: Fast, cost-effective for generation
- **Reviewer (`gpt-4.1`)**: Thorough, high-quality evaluation

### Cost Optimization

- Use faster worker model for draft generation
- Use premium reviewer model for quality gate
- Typical workflow: 1-3 iterations per query

### Timeout

- Default client timeout: 60 seconds
- Adjust based on query complexity
- Long queries may require higher timeout

---

## Related Documentation

- **Workflow Implementation**: `src/agenticfleet/workflows/workflow_as_agent.py`
- **Integration Guide**: `docs/features/workflow-as-agent-integration.md`
- **Architecture**: `docs/architecture/workflow-as-agent.md`
- **E2E Tests**: `tests/e2e/TESTING.md`

---

## API Comparison

### Old Way (Generic)

```bash
POST /v1/responses
{
  "model": "workflow_as_agent",
  "input": {"text": "Your query"}
}
```

### New Way (Dedicated) ✨

```bash
POST /v1/workflow/reflection
{
  "query": "Your query",
  "worker_model": "gpt-4.1-nano",
  "reviewer_model": "gpt-4.1"
}
```

The dedicated endpoint provides:

- Clearer intent
- Explicit model control
- Better documentation
- Simplified request format
- Purpose-built for reflection pattern

---

## Status Codes

| Code | Meaning               | Description                            |
| ---- | --------------------- | -------------------------------------- |
| 200  | OK                    | Workflow started, SSE stream initiated |
| 400  | Bad Request           | Invalid or missing parameters          |
| 404  | Not Found             | Conversation ID not found              |
| 500  | Internal Server Error | Workflow execution failure             |

---

## Changelog

### v0.5.3 (2025-10-19)

- ✨ Added dedicated `/v1/workflow/reflection` endpoint
- ✅ Full SSE streaming support
- ✅ Conversation persistence
- ✅ Custom model selection
- ✅ Comprehensive error handling
- ✅ Test suite included

---

**Ready to use!** The reflection workflow endpoint is fully functional and tested. 🚀
