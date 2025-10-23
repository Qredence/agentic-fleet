# AgenticFleet API Reference

## Overview

AgenticFleet provides a RESTful HTTP API and Server-Sent Events (SSE) streaming interface for interacting with the multi-agent orchestration system.

## Base URL

```
Development: http://localhost:8000
Production: https://your-domain.com
```

## Authentication

Currently, AgenticFleet uses API key authentication via environment variables:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-key

# Optional configurations
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4317
```

## Core API Endpoints

### Health Check

```http
GET /health
```

Returns system health status and configuration information.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.5.4",
  "features": {
    "checkpointing": true,
    "human_in_the_loop": true,
    "memory": false
  }
}
```

### Conversation Management

#### List Conversations

```http
GET /v1/conversations
```

Retrieve all conversation IDs and metadata.

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv_12345",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T11:45:00Z",
      "message_count": 15,
      "status": "active"
    }
  ]
}
```

#### Create New Conversation

```http
POST /v1/conversations
Content-Type: application/json
```

**Request Body:**
```json
{
  "task": "Analyze the market trends for Q1 2025",
  "workflow_id": "optional_workflow_id",
  "checkpoint_id": "optional_checkpoint_id"
}
```

**Response:**
```json
{
  "conversation_id": "conv_12345",
  "stream_url": "/v1/conversations/conv_12345/stream",
  "status": "started"
}
```

#### Get Conversation Details

```http
GET /v1/conversations/{conversation_id}
```

Retrieve conversation metadata and message history.

**Response:**
```json
{
  "id": "conv_12345",
  "created_at": "2025-01-15T10:30:00Z",
  "status": "active",
  "messages": [
    {
      "id": "msg_001",
      "type": "user",
      "content": "Analyze the market trends for Q1 2025",
      "timestamp": "2025-01-15T10:30:00Z"
    }
  ],
  "metadata": {
    "agent_interactions": 8,
    "tool_calls": 12,
    "tokens_used": 15420
  }
}
```

### Checkpoint Management

#### List Checkpoints

```http
GET /v1/checkpoints
```

Retrieve all available checkpoints.

**Response:**
```json
{
  "checkpoints": [
    {
      "id": "checkpoint_001",
      "workflow_id": "magentic_fleet_abc123",
      "created_at": "2025-01-15T10:45:00Z",
      "round_count": 5,
      "status": "resumable"
    }
  ]
}
```

#### Resume from Checkpoint

```http
POST /v1/conversations
Content-Type: application/json
```

**Request Body:**
```json
{
  "task": "Continue market analysis",
  "checkpoint_id": "checkpoint_001"
}
```

### Agent Configuration

#### Get Available Agents

```http
GET /v1/agents
```

Retrieve all available agents and their capabilities.

**Response:**
```json
{
  "agents": [
    {
      "name": "orchestrator",
      "model": "gpt-5",
      "capabilities": ["planning", "coordination", "synthesis"],
      "tools": []
    },
    {
      "name": "researcher",
      "model": "gpt-5",
      "capabilities": ["web_search", "information_gathering"],
      "tools": ["web_search_tool"]
    },
    {
      "name": "coder",
      "model": "gpt-5-codex",
      "capabilities": ["code_execution", "code_analysis", "computation"],
      "tools": ["code_interpreter_tool"]
    },
    {
      "name": "analyst",
      "model": "gpt-5",
      "capabilities": ["data_analysis", "visualization", "insights"],
      "tools": ["data_analysis_tool", "visualization_suggestion_tool"]
    }
  ]
}
```

### Human-in-the-Loop (HITL) Approval

#### Get Pending Approvals

```http
GET /v1/approvals
```

Retrieve all pending human approval requests.

**Response:**
```json
{
  "approvals": [
    {
      "id": "approval_001",
      "conversation_id": "conv_12345",
      "operation_type": "code_execution",
      "description": "Execute Python code for data analysis",
      "details": {
        "code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head())"
      },
      "timeout_seconds": 300,
      "created_at": "2025-01-15T11:30:00Z",
      "status": "pending"
    }
  ]
}
```

#### Submit Approval Decision

```http
POST /v1/approvals/{approval_id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "decision": "approve",
  "modified_details": {
    "code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head())\nprint('Analysis complete')"
  }
}
```

**Decision Options:**
- `"approve"` - Approve the operation as requested
- `"reject"` - Reject the operation entirely
- `"modify"` - Approve with modifications (include `modified_details`)

**Response:**
```json
{
  "status": "success",
  "message": "Approval decision recorded",
  "conversation_id": "conv_12345"
}
```

## Server-Sent Events (SSE) Streaming

### Stream Conversation Events

```http
GET /v1/conversations/{conversation_id}/stream
Accept: text/event-stream
```

Connect to real-time stream of conversation events.

#### Event Types

**Agent Response Delta:**
```json
{
  "type": "response.output_text.delta",
  "data": {
    "agent_name": "researcher",
    "content": "Based on my analysis of Q1 2025 market"
  }
}
```

**Agent Response Complete:**
```json
{
  "type": "response.completed",
  "data": {
    "agent_name": "researcher",
    "model": "gpt-5",
    "tokens_used": 1250,
    "duration_ms": 3500
  }
}
```

**Function Call Request:**
```json
{
  "type": "function_call.requested",
  "data": {
    "agent_name": "coder",
    "function_name": "code_interpreter_tool",
    "arguments": {
      "code": "print('Hello, AgenticFleet!')",
      "language": "python"
    }
  }
}
```

**Function Call Result:**
```json
{
  "type": "function_call.completed",
  "data": {
    "function_name": "code_interpreter_tool",
    "result": {
      "output": "Hello, AgenticFleet!\n",
      "exit_code": 0,
      "execution_time_ms": 1250
    }
  }
}
```

**Plan Creation:**
```json
{
  "type": "workflow.plan.created",
  "data": {
    "manager_agent": "orchestrator",
    "plan_steps": [
      "1. Research market trends using researcher agent",
      "2. Analyze findings using analyst agent",
      "3. Generate summary report"
    ]
  }
}
```

**Progress Ledger Update:**
```json
{
  "type": "workflow.progress_ledger.updated",
  "data": {
    "round_number": 3,
    "agent_name": "analyst",
    "satisfaction_rating": 0.7,
    "is_stalling": false,
    "next_agent": "orchestrator",
    "reasoning": "Analysis completed with good insights, proceeding to synthesis"
  }
}
```

**Final Answer:**
```json
{
  "type": "final_answer.completed",
  "data": {
    "agent_name": "orchestrator",
    "final_answer": "Based on comprehensive analysis of Q1 2025 market data...",
    "total_rounds": 5,
    "total_tokens": 3450,
    "execution_time_ms": 12500
  }
}
```

**Error Events:**
```json
{
  "type": "error.occurred",
  "data": {
    "error_code": "AGENT_EXECUTION_FAILED",
    "message": "Coder agent failed to execute code",
    "agent_name": "coder",
    "details": "SyntaxError in line 2: invalid syntax"
  }
}
```

## Error Handling

### HTTP Status Codes

- `200 OK` - Successful request
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Missing or invalid API key
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server-side error

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid task description provided",
    "details": {
      "field": "task",
      "issue": "Must be between 10 and 1000 characters"
    }
  }
}
```

## Rate Limiting

- **Standard Rate Limit**: 100 requests per minute
- **Burst Rate Limit**: 200 requests per minute for 1 minute
- **Streaming Connections**: 5 concurrent SSE connections per IP

## SDK and Client Libraries

### Python Client

```python
from agenticfleet import AgenticFleetClient

# Initialize client
client = AgenticFleetClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Start conversation
conversation = client.create_conversation(
    task="Analyze market trends for Q1 2025"
)

# Stream events
for event in conversation.stream():
    if event.type == "final_answer.completed":
        print(f"Result: {event.data.final_answer}")
    elif event.type == "error.occurred":
        print(f"Error: {event.data.message}")
```

### JavaScript/TypeScript Client

```typescript
import { AgenticFleetClient } from '@agenticfleet/client';

const client = new AgenticFleetClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

const conversation = await client.createConversation({
  task: 'Analyze market trends for Q1 2025'
});

for await (const event of conversation.stream()) {
  switch (event.type) {
    case 'final_answer.completed':
      console.log('Result:', event.data.finalAnswer);
      break;
    case 'error.occurred':
      console.error('Error:', event.data.message);
      break;
  }
}
```

## Development and Testing

### Local Development

Start the development server:

```bash
make haxui-server
```

The API will be available at `http://localhost:8000`.

### API Testing

Use the included test suite:

```bash
# Run API tests
uv run pytest tests/test_haxui_api.py -v

# Run with coverage
uv run pytest --cov=agenticfleet.haxui --cov-report=term-missing
```

### Integration Testing

Test SSE streaming:

```bash
curl -N http://localhost:8000/v1/conversations/test/stream \
  -H "Accept: text/event-stream"
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|------------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for LLM access |
| `ENABLE_OTEL` | No | false | Enable OpenTelemetry tracing |
| `OTLP_ENDPOINT` | No | http://localhost:4317 | OpenTelemetry collector endpoint |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARN, ERROR) |
| `MAX_CONVERSATION_LENGTH` | No | 100 | Maximum messages per conversation |
| `CHECKPOINT_RETENTION_DAYS` | No | 30 | Days to retain checkpoints |

### Feature Flags

Control experimental features via environment variables:

```bash
# Enable memory integration
ENABLE_MEMORY=true

# Enable advanced caching
ENABLE_ADVANCED_CACHING=true

# Enable debug mode
DEBUG_MODE=true
```

## Security Considerations

- **API Key Security**: Never commit API keys to version control
- **CORS Configuration**: Configure allowed origins for production
- **Input Validation**: All inputs are validated using Pydantic models
- **Rate Limiting**: Implement client-side rate limiting for production
- **HTTPS**: Use HTTPS in production environments
- **Sanitization**: User inputs are sanitized before processing

## Monitoring and Observability

### OpenTelemetry Integration

Enable distributed tracing:

```bash
export ENABLE_OTEL=true
export OTLP_ENDPOINT=http://localhost:4317
```

Metrics collected:
- Request latency and duration
- Agent execution times
- Token usage tracking
- Error rates and types
- Checkpoint creation/resume events

### Logging

Structured logging format:

```json
{
  "timestamp": "2025-01-15T11:30:00Z",
  "level": "INFO",
  "component": "haxui.api",
  "conversation_id": "conv_12345",
  "agent_name": "researcher",
  "event_type": "function_call.completed",
  "duration_ms": 1250,
  "message": "Web search completed successfully"
}
```

## Versioning

API versioning follows semantic versioning:

- **v1.0.x**: Stable API with backward compatibility
- **Breaking changes**: Increment major version
- **New features**: Increment minor version
- **Bug fixes**: Increment patch version

Current version: **v1.0** (stable)

For more details, see the [API Changelog](./api/changelog.md).
