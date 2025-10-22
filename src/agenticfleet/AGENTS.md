# AGENTS.md - Python Package Development

> **Agent instructions for working with the `agenticfleet` Python package**

This file provides guidance for AI coding agents working specifically within the `src/agenticfleet/` Python package. For general project instructions, see the [root AGENTS.md](../../docs/project/AGENTS.md).

---

## Package Overview

The `agenticfleet` package contains the core implementation of the multi-agent orchestration system. It's organized into specialized modules handling different aspects of the system.

### Package Structure

```
src/agenticfleet/
├── __init__.py              # Package initialization, exports
├── __main__.py              # CLI entry point (python -m agenticfleet)
├── agents/                  # Agent implementations
│   ├── analyst/            # Data analysis specialist
│   ├── coder/              # Code generation specialist
│   ├── orchestrator/       # Magentic manager
│   └── researcher/         # Information gathering specialist
├── cli/                     # Command-line interface
│   ├── repl.py             # Interactive REPL with Rich UI
│   └── ui.py               # Console UI components
├── config/                  # Configuration management
│   ├── settings.py         # Settings loader (env + YAML)
│   └── workflow.yaml       # Workflow configuration
├── context/                 # Context and memory providers
│   └── mem0_provider.py    # Mem0 integration
├── core/                    # Core utilities and types
│   ├── approval.py         # HITL approval interfaces
│   ├── code_types.py       # Tool response types (Pydantic)
│   ├── exceptions.py       # Custom exceptions
│   └── logging.py          # Logging setup
├── fleet/                   # Orchestration layer
│   ├── callbacks.py        # Event callbacks
│   ├── fleet_builder.py    # Builder pattern for fleet
│   └── magentic_fleet.py   # Magentic One implementation
├── haxui/                   # Web API
│   ├── api.py              # FastAPI endpoints
│   ├── runtime.py          # Fleet runtime wrapper
│   └── web_approval.py     # Web approval handler
├── observability.py         # OpenTelemetry tracing setup
├── skills/                  # Reusable skill modules
└── workflows/               # Workflow implementations
    └── workflow_as_agent.py # Worker/Reviewer reflection pattern
```

---

## Module-Specific Guidelines

### Working with Agents (`agents/`)

#### Agent Factory Pattern

Every agent follows this structure:

```python
# agents/<role>/agent.py
from agent_framework import ChatAgent
from agent_framework_azure_ai import OpenAIResponsesClient
from agenticfleet.config.settings import Settings

def create_<role>_agent() -> ChatAgent:
    """Create the <role> agent with configured tools."""
    settings = Settings()
    config = settings.load_agent_config("<role>")

    client = OpenAIResponsesClient(model_id=config["model"])

    # Load tools from config
    tools = []
    for tool_config in config.get("tools", []):
        if tool_config.get("enabled", False):
            # Import and add tool
            ...

    return ChatAgent(
        name=config["name"],
        model_client=client,
        system_message=config["system_prompt"],
        tools=tools
    )
```

#### Agent Configuration (`agents/<role>/config.yaml`)

```yaml
name: "<Role> Agent"
model: "gpt-5" # Never hardcode in Python
system_prompt: | # Complete agent instructions
  You are a specialist...
temperature: 0.7
max_tokens: 4000
runtime:
  stream: true # Enable streaming
  store: false # Disable conversation storage
  checkpoint: true # Enable checkpointing
tools:
  - name: tool_name
    enabled: true
```

#### Tool Implementation (`agents/<role>/tools/<tool>.py`)

All tools MUST:

1. Return Pydantic models from `core/code_types.py`
2. Have complete type hints
3. Include docstrings
4. Handle errors gracefully

```python
from agenticfleet.core.code_types import WebSearchResponse

def web_search_tool(query: str, limit: int = 5) -> WebSearchResponse:
    """
    Search the web for information.

    Args:
        query: Search query string
        limit: Maximum number of results

    Returns:
        WebSearchResponse with results or error
    """
    try:
        # Implementation
        return WebSearchResponse(
            success=True,
            results=[...],
            message=f"Found {len(results)} results"
        )
    except Exception as e:
        return WebSearchResponse(
            success=False,
            results=[],
            error=str(e)
        )
```

---

### Configuration Management (`config/`)

#### Settings Loading Pattern

```python
from agenticfleet.config.settings import Settings

# Always use the Settings singleton
settings = Settings()

# Load agent config
agent_config = settings.load_agent_config("researcher")

# Access workflow config
workflow_config = settings.workflow_config

# Get environment variables with fallbacks
model = settings.openai_model  # Falls back to default
```

#### YAML Configuration

- **workflow.yaml**: Fleet-level settings (manager instructions, HITL, checkpointing)
- **agents/\<role\>/config.yaml**: Per-agent settings (model, prompts, tools)
- **.env**: API keys, endpoints, feature flags

**Rule**: Configuration changes go in YAML, not Python code.

---

### Fleet Orchestration (`fleet/`)

#### Building a Fleet

```python
from agenticfleet.fleet.fleet_builder import FleetBuilder
from agent_framework import FileCheckpointStorage

# Build fleet with builder pattern
builder = FleetBuilder()
fleet = (builder
    .with_manager()
    .with_agents()
    .with_checkpointing(FileCheckpointStorage(path="./var/checkpoints"))
    .with_callbacks()
    .with_approval_handler(approval_handler)
    .build())

# Run workflow
result = await fleet.run(
    task="Analyze this data...",
    resume_from_checkpoint=None
)
```

#### Callback System (`fleet/callbacks.py`)

Callbacks provide observability hooks:

```python
from agenticfleet.fleet.callbacks import ConsoleCallbacks

callbacks = ConsoleCallbacks(
    streaming_enabled=True,
    plan_logging=True,
    progress_logging=True
)

# Register with fleet
fleet = FleetBuilder().with_callbacks(callbacks).build()
```

Available callbacks:

- `streaming_agent_response_callback` - Stream agent outputs
- `plan_creation_callback` - Log manager plans
- `progress_ledger_callback` - Track progress evaluations
- `tool_call_callback` - Monitor tool executions
- `final_answer_callback` - Capture results

---

### Human-in-the-Loop (`core/approval.py`, `haxui/web_approval.py`)

#### Approval Interfaces

```python
from agenticfleet.core.approval import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalDecision,
    ApprovalHandler
)

# Create approval request
request = ApprovalRequest(
    request_id="unique_id",
    operation_type="code_execution",
    description="Execute Python code",
    details={"code": "print('hello')"},
    timeout_seconds=300
)

# Handle approval
response = await approval_handler.request_approval(request)

if response.decision == ApprovalDecision.APPROVE:
    # Execute operation
    ...
elif response.decision == ApprovalDecision.REJECT:
    # Cancel operation
    ...
elif response.decision == ApprovalDecision.MODIFY:
    # Use modified data
    modified_code = response.modified_data.get("code")
```

#### CLI vs Web Handlers

- **CLIApprovalHandler** (`core/cli_approval.py`): Terminal prompts
- **WebApprovalHandler** (`haxui/web_approval.py`): SSE events + POST endpoint

Both implement the `ApprovalHandler` ABC.

---

### Web API (`haxui/`)

#### FastAPI Endpoints (`haxui/api.py`)

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI(title="AgenticFleet API")

@app.post("/v1/responses")
async def create_response(request: ChatRequest):
    """OpenAI-compatible SSE streaming endpoint."""
    async def event_stream():
        # Stream ResponseStreamEvent objects
        ...

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )
```

#### SSE Event Format

All events follow OpenAI Responses API format:

```typescript
// content_block_delta - Text chunk
{
  "type": "content_block_delta",
  "delta": { "type": "text", "text": "..." }
}

// response_output_item_done - Message complete
{
  "type": "response_output_item_done",
  "item": { ... }
}

// approval_required - HITL gate
{
  "type": "approval_required",
  "request_id": "...",
  "operation_type": "code_execution",
  "details": { ... }
}
```

---

### Observability (`observability.py`)

#### Tracing Setup

```python
from agenticfleet.observability import setup_tracing, is_tracing_enabled

# Initialize tracing (called in __main__.py and haxui/api.py)
if is_tracing_enabled():
    setup_tracing()
```

#### Environment Variables

- `ENABLE_OTEL=true` - Enable OpenTelemetry
- `ENABLE_SENSITIVE_DATA=true` - Capture prompts/completions
- `OTLP_ENDPOINT=localhost:4317` - OTLP collector endpoint

---

## Development Patterns

### Import Organization

Follow Ruff's isort rules:

```python
# Standard library
import asyncio
import logging
from pathlib import Path

# Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# Microsoft Agent Framework
from agent_framework import ChatAgent
from agent_framework_azure_ai import OpenAIResponsesClient

# Local
from agenticfleet.config.settings import Settings
from agenticfleet.core.code_types import CodeExecutionResult
```

### Type Hints

Always specify types:

```python
# ✅ CORRECT
def process(data: str | None) -> Result:
    ...

async def fetch(url: str) -> dict[str, Any]:
    ...

# ❌ WRONG
def process(data):
    ...
```

### Error Handling

Use custom exceptions from `core/exceptions.py`:

```python
from agenticfleet.core.exceptions import (
    AgenticFleetError,
    AgentConfigurationError,
    WorkflowError,
    ToolExecutionError
)

def create_agent() -> ChatAgent:
    try:
        config = settings.load_agent_config("researcher")
    except FileNotFoundError:
        raise AgentConfigurationError(
            "Agent config not found: researcher"
        )
```

### Logging

Use structured logging:

```python
from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)

logger.info("Starting workflow", extra={"task": task})
logger.error("Tool execution failed", extra={"tool": tool_name, "error": str(e)})
```

---

## Testing Within the Package

### Unit Testing Agent Factories

```python
# tests/test_config.py
def test_researcher_agent():
    settings = Settings()
    config = settings.load_agent_config("researcher")

    assert config["model"] is not None
    assert "system_prompt" in config
    assert "tools" in config
```

### Mocking Client Calls

```python
from unittest.mock import MagicMock, AsyncMock
from agent_framework_azure_ai import OpenAIResponsesClient

mock_client = MagicMock(spec=OpenAIResponsesClient)
mock_client.create_response = AsyncMock(return_value=mock_response)
```

### Testing Workflows

```python
# tests/test_magentic_fleet.py
@pytest.mark.asyncio
async def test_fleet_orchestration():
    fleet = FleetBuilder().with_manager().with_agents().build()

    result = await fleet.run("Test task")

    assert result is not None
    # More assertions...
```

---

## Code Quality Checks

Before committing changes to the package:

```bash
# Lint
uv run ruff check src/agenticfleet/

# Format
uv run black src/agenticfleet/

# Type check
uv run mypy src/agenticfleet/

# Run package tests
uv run pytest tests/test_config.py -v
```

---

## Common Tasks

### Adding a New Agent

1. Create directory: `mkdir -p agents/<role>/tools`
2. Add factory in `agents/<role>/agent.py`
3. Create config: `agents/<role>/config.yaml`
4. Export in `agents/__init__.py`
5. Register in `fleet/fleet_builder.py`
6. Update manager instructions in `config/workflow.yaml`
7. Add tests in `tests/test_config.py`

### Adding a Tool

1. Implement in `agents/<role>/tools/<tool>.py`
2. Add to `agents/<role>/config.yaml` tools list
3. Update agent's system_prompt
4. Add unit tests
5. Validate: `uv run python tests/test_config.py`

### Modifying Workflow Config

1. Edit `config/workflow.yaml`
2. Validate: `uv run python tests/test_config.py`
3. Test integration: `uv run pytest tests/test_magentic_fleet.py -v`

### Adding API Endpoint

1. Add route to `haxui/api.py`
2. Update `FleetRuntime` if needed
3. Add tests in `tests/test_haxui_api.py`
4. Document in `docs/api/`

---

## Integration Points

### With Frontend

- **SSE Events**: Backend emits via `haxui/api.py`, frontend consumes via `useFastAPIChat` hook
- **Approval Flow**: `WebApprovalHandler` stores requests, frontend POSTs decisions
- **Health Check**: `/health` endpoint for status monitoring

### With CLI

- **REPL**: `cli/repl.py` uses `FleetBuilder` to create fleet
- **Callbacks**: `ConsoleCallbacks` for Rich-based UI updates
- **Approval**: `CLIApprovalHandler` for terminal prompts

### With Microsoft Agent Framework

- **Agents**: All agents use `ChatAgent` from `agent_framework`
- **Clients**: Use `OpenAIResponsesClient` from `agent_framework_azure_ai`
- **Checkpoints**: Use `FileCheckpointStorage` / `InMemoryCheckpointStorage`
- **Tracing**: Microsoft Agent Framework's built-in OpenTelemetry

---

## Performance Considerations

### Streaming

Always enable streaming for better UX:

```yaml
# agents/<role>/config.yaml
runtime:
  stream: true
```

### Checkpointing

Use checkpoints to avoid redundant LLM calls:

```python
storage = FileCheckpointStorage(path="./var/checkpoints")
fleet = FleetBuilder().with_checkpointing(storage).build()

# Resume from checkpoint
result = await fleet.run(task, resume_from_checkpoint=checkpoint_id)
```

### Async Operations

Use async/await consistently:

```python
# ✅ CORRECT
async def run_workflow(task: str) -> str:
    result = await fleet.run(task)
    return result

# ❌ WRONG - Don't mix sync/async
def run_workflow(task: str) -> str:
    result = asyncio.run(fleet.run(task))  # Avoid
    return result
```

---

## Security Best Practices

### Approval Required Operations

Always require approval for:

- Code execution
- File operations
- API calls with side effects
- Database modifications

```python
# Wrap sensitive operations
if approval_handler:
    request = create_approval_request(
        operation_type="code_execution",
        details={"code": code}
    )
    response = await approval_handler.request_approval(request)

    if response.decision != ApprovalDecision.APPROVE:
        return ErrorResult("Operation not approved")
```

### Input Validation

Use Pydantic for all API inputs:

```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    model: str = Field(default="workflow_as_agent")
    max_tokens: int = Field(default=4000, ge=1, le=32000)
```

### Environment Variables

Never commit secrets. Use `.env` file:

```python
from agenticfleet.config.settings import Settings

settings = Settings()
api_key = settings.openai_api_key  # From .env
```

---

## References

- **Root AGENTS.md**: `../../docs/project/AGENTS.md` (general project instructions)
- **Package README**: `../../README.md` (user-facing documentation)
- **Architecture Docs**: `../../docs/architecture/`
- **API Docs**: `../../docs/api/`
- **Microsoft Agent Framework**: https://github.com/microsoft/agent-framework/python/

---

## Package-Specific Notes

- All public APIs are exported via `__init__.py`
- Use `__main__.py` for CLI entry point (enables `python -m agenticfleet`)
- Keep `py.typed` file for PEP 561 type hint support
- Runtime state lives in `var/` (checkpoints, logs, memories)
- Configuration lives in `config/` and agent directories
- Never bypass YAML configuration—it's the source of truth
