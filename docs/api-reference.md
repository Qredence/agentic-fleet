# API Reference

## FastAPI Endpoints

### POST /run

Execute a workflow with the given message.

#### Request Schema

```json
{
  "message": "string",
  "metadata": {
    "team_id": "string"
  },
  "team_id": "string"
}
```

#### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | `string` | Yes | The user's input message/task |
| `metadata` | `object` | No | Optional metadata (e.g., `entity_id`) |
| `metadata.entity_id` | `string` | No | Agent/workflow entity ID |
| `team_id` | `string` | No | Override team (research/coding/default) |

#### Response Schema

```json
{
  "outputs": [
    {
      "content": [
        {
          "text": "string"
        }
      ]
    }
  ],
  "trace": [
    {
      "executor_id": "string",
      "status": "string"
    }
  ]
}
```

#### Example Request

```bash
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Research the latest AI developments in 2024",
    "team_id": "research"
  }'
```

#### Example Response

```json
{
  "outputs": [
    {
      "content": [
        {
          "text": "Based on my research, here are the key AI developments in 2024..."
        }
      ]
    }
  ],
  "trace": [
    {
      "executor_id": "Router",
      "status": "completed"
    },
    {
      "executor_id": "Planner",
      "status": "completed"
    },
    {
      "executor_id": "Worker",
      "status": "completed"
    },
    {
      "executor_id": "Judge",
      "status": "completed"
    }
  ]
}
```

---

### POST /train

Compile the DSPy optimizer with training examples.

#### Request Schema

```json
{
  "examples": [
    {
      "task": "string",
      "context": {
        "team_id": "string",
        "constraints": ["string"],
        "tools": ["string"]
      },
      "plan": "string",
      "result": "string"
    }
  ]
}
```

#### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `examples` | `array` | Yes | Training examples |
| `examples[].task` | `string` | Yes | Task description |
| `examples[].context` | `object` | Yes | Team context |
| `examples[].context.team_id` | `string` | Yes | Team identifier |
| `examples[].context.constraints` | `array` | No | Task constraints |
| `examples[].context.tools` | `array` | No | Available tools |
| `examples[].plan` | `string` | Yes | Expected plan |
| `examples[].result` | `string` | Yes | Expected result |

#### Response Schema

```json
{
  "output_path": "string",
  "examples_used": "integer"
}
```

#### Example Request

```bash
curl -X POST "http://localhost:8000/train" \
  -H "Content-Type: application/json" \
  -d '{
    "examples": [
      {
        "task": "Research AI trends",
        "context": {
          "team_id": "research",
          "constraints": [],
          "tools": ["browser", "search"]
        },
        "plan": "1. Search for recent AI news\n2. Read top articles\n3. Summarize findings",
        "result": "Research complete with key trends identified"
      }
    ]
  }'
```

#### Example Response

```json
{
  "output_path": "dspy_modules/state/planner_opt.json",
  "examples_used": 10
}
```

---

## Data Models

### TaskContext

Context passed into planner/worker modules.

```python
class TaskContext(BaseModel):
    team_id: str
    constraints: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
```

| Field | Type | Description |
|-------|------|-------------|
| `team_id` | `str` | Current team (research/coding/default) |
| `constraints` | `list[str]` | Task constraints |
| `tools` | `list[str]` | Available tools |

### ExecutionResult

Normalized worker output.

```python
class ExecutionResult(BaseModel):
    status: str  # "success", "error", "pending"
    content: str
    artifacts: list[str] = Field(default_factory=list)
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | Execution status |
| `content` | `str` | Result content |
| `artifacts` | `list[str]` | Output artifacts |

### RoutingDecision

Router output containing pattern and target team.

```python
class RoutingDecision(BaseModel):
    pattern: str  # "direct", "simple", "complex"
    target_team: str
    reasoning: str
```

| Field | Type | Description |
|-------|------|-------------|
| `pattern` | `str` | Routing pattern |
| `target_team` | `str` | Target team name |
| `reasoning` | `str` | Reasoning for decision |

---

## Team Registry

### TeamConfig

```python
class TeamConfig(TypedDict):
    tools: list[str]
    credentials: dict
    description: str
```

### Available Teams

| Team | Tools | Description |
|------|-------|-------------|
| `research` | browser, search, synthesize | Web research and synthesis |
| `coding` | repo_read, repo_write, tests | Code changes and validation |
| `default` | general | Generalist fallback |

### List Teams

```python
from agentic_fleet.config import list_teams

teams = list_teams()  # ["research", "coding", "default"]
```

---

## DSPy Signatures

### RouterSignature

```python
class RouterSignature(dspy.Signature):
    """Route task to appropriate team and pattern."""
    task: str = dspy.InputField(desc="the user's task description")
    decision: RoutingDecision = dspy.OutputField(desc="routing decision")
```

### PlannerSignature

```python
class PlannerSignature(dspy.Signature):
    """Create execution plan for complex tasks."""
    task: str = dspy.InputField(desc="the user's task")
    context: TaskContext = dspy.InputField(desc="team context")
    plan: str = dspy.OutputField(desc="step-by-step execution plan")
    reasoning: str = dspy.OutputField(desc="reasoning for the plan")
```

### WorkerSignature

```python
class WorkerSignature(dspy.Signature):
    """Execute a single step of the plan."""
    step: str = dspy.InputField(desc="the step to execute")
    context: TaskContext = dspy.InputField(desc="team context")
    action: str = dspy.OutputField(desc="action taken")
    result: ExecutionResult = dspy.OutputField(desc="execution result")
```

### JudgeSignature

```python
class JudgeSignature(dspy.Signature):
    """Review and approve/reject worker output."""
    original_task: str = dspy.InputField(desc="original user task")
    result: ExecutionResult = dspy.InputField(desc="worker result to review")
    is_approved: bool = dspy.OutputField(desc="whether result meets quality bar")
    critique: str = dspy.OutputField(desc="feedback for revision if rejected")
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LITELLM_PROXY_URL` | Yes | - | LiteLLM proxy URL |
| `LITELLM_SERVICE_KEY` | Yes | - | LiteLLM service key |
| `DSPY_MODEL` | No | deepseek-v3.2 | DSPy model name |
| `DSPY_TEMPERATURE` | No | 0 | Model temperature |
| `DSPY_MAX_TOKENS` | No | 4096 | Max output tokens |
| `DATABASE_URL` | No | - | PostgreSQL connection |

---

## Error Handling

### HTTP Errors

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid input |
| 422 | Validation Error - Pydantic validation failed |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Proxy not reachable |

### Error Response Schema

```json
{
  "detail": "string"
}
```

### Common Errors

```json
// 422 - Validation Error
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

// 500 - Internal Error
{
  "detail": "Agent execution failed: ..."
}
```

---

## Health Check

### GET /health

Check if the service is healthy.

#### Response

```json
{
  "status": "healthy",
  "proxy_connected": true
}
```

---

## Curl Examples

### Basic Run

```bash
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Tokyo?"}'
```

### Run with Team Override

```bash
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Research LLM developments",
    "team_id": "research"
  }'
```

### Train with Examples

```bash
curl -X POST "http://localhost:8000/train" \
  -H "Content-Type: application/json" \
  -d '{
    "examples": [
      {
        "task": "Simple question",
        "context": {"team_id": "default", "constraints": [], "tools": []},
        "plan": "Direct answer",
        "result": "Answer provided"
      }
    ]
  }'
```

### Health Check

```bash
curl "http://localhost:8000/health"
```
