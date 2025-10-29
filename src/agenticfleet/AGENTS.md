# AGENTS.md – agenticfleet/ (Python Backend)

> Agent-focused guide for working in the `src/agenticfleet/` Python package. This is the core backend implementation of AgenticFleet's multi-agent orchestration system.

---

## Quick Start

**Essential backend commands (from repository root):**

```bash
# Setup
make install          # Install all dependencies
uv sync              # Sync from lockfile

# Run application
uv run agentic-fleet  # Full stack (backend + frontend)
uv run fleet         # CLI/REPL only
make backend         # Backend only (port 8000)

# Configuration validation (CRITICAL before commits)
make test-config

# Testing
uv run pytest tests/test_workflow.py -v
uv run pytest -k "test_name" -v

# Code quality
make check           # Lint + type-check
make format          # Auto-format code
```

**CRITICAL**: Always prefix Python commands with `uv run`. Never use `pip` or `python` directly.

---

## Package Structure

```
agenticfleet/
├── __init__.py              # Package initialization
├── server.py                # FastAPI application with WebSocket support
├── workflow.py              # Workflow execution and orchestration
├── magentic_fleet.yaml      # Fleet configuration
│
├── agents/                  # Agent implementations
│   ├── orchestrator/       # Manager/orchestrator agent
│   ├── researcher/         # Research agent
│   ├── coder/             # Code generation agent
│   └── analyst/           # Data analysis agent
│
├── api/                    # API layer
│   ├── models/            # Pydantic models
│   │   ├── chat_models.py  # Chat request/response schemas
│   │   ├── sse_events.py   # SSE event types
│   │   └── workflow_config.py # Workflow configuration
│   ├── event_collector.py  # Event buffering for streaming
│   ├── event_translator.py # Event format conversion
│   ├── redis_client.py     # Redis state persistence
│   ├── websocket_manager.py # WebSocket connection manager
│   └── workflow_factory.py # Workflow creation
│
├── cli/                    # Command-line interface
│   └── memory_cli.py       # Memory management CLI
│
├── memory/                 # Memory integration
│   ├── config.py          # Memory configuration
│   ├── context_provider.py # Context retrieval
│   ├── manager.py         # Memory lifecycle
│   ├── mcp_integration.py  # MCP server integration
│   ├── models.py          # Memory data models
│   └── workflow_integration.py # Workflow memory hooks
│
└── persistance/            # Data persistence
    └── database.py        # Database layer
```

---

## Core Concepts

### 1. Workflow System

AgenticFleet uses Microsoft Agent Framework's orchestration patterns:

- **WorkflowFactory** (`api/workflow_factory.py`): Creates workflow instances
- **Workflow execution** (`workflow.py`): Manages agent interactions
- **Configuration**: YAML-driven (never hardcode behavior)

**Workflow types:**

- `magentic_fleet` - Multi-agent orchestration with manager
- `collaboration` - Peer-to-peer agent collaboration

### 2. Agent Architecture

Each agent lives in `agents/<role>/`:

- `agent.py` - Factory function returning `ChatAgent`
- `config.yaml` - Model, system prompt, tools configuration
- `tools/` - Agent-specific tools as Python modules

**Key principle**: Configuration in YAML, wiring in Python. Never hardcode models or prompts.

### 3. API Layer

**FastAPI Server** (`server.py`):

- POST `/v1/chat` - Create execution, return WebSocket URL
- WebSocket `/ws/chat/{id}` - Real-time event streaming
- GET `/v1/chat/executions/{id}` - Poll execution status
- GET `/health` - Health check

**Event Flow**:

```
Client → POST /v1/chat → WorkflowFactory → workflow.run()
    ↓
EventCollector buffers events → WebSocket streaming → Client
    ↓
Redis persistence (execution state)
```

### 4. Memory System

**Mem0 Integration** (`memory/`):

- Long-term memory storage via Azure AI Search
- Context retrieval for agent prompts
- MCP server integration for memory tools

**Status**: Exported but not yet wired into workflow prompts.

---

## Development Patterns

### Adding a New Agent

1. **Create structure**:

   ```bash
   mkdir -p src/agenticfleet/agents/new_agent/tools
   touch src/agenticfleet/agents/new_agent/{agent.py,config.yaml,__init__.py}
   ```

2. **Implement factory** (`agents/new_agent/agent.py`):

   ```python
   from agent_framework.core import ChatAgent
   from agenticfleet.config import Settings

   def create_new_agent() -> ChatAgent:
       """Create the new agent with tools."""
       settings = Settings()
       config = settings.load_agent_config("new_agent")

       client = OpenAIResponsesClient(model_id=config["model"])
       # Load tools from config...

       return ChatAgent(
           name=config["name"],
           model_client=client,
           system_message=config["system_prompt"],
           tools=tools
       )
   ```

3. **Configure** (`agents/new_agent/config.yaml`):

   ```yaml
   name: "New Agent"
   model: "gpt-5" # NEVER hardcode in Python
   system_prompt: "You are a specialist in..."
   tools:
     - name: tool_name
       enabled: true
   ```

4. **Register**:
   - Export in `agents/__init__.py`
   - Add to workflow configuration
   - Update manager instructions

5. **Validate**: `make test-config`

### Adding a Tool

1. **Implement** (`agents/<role>/tools/new_tool.py`):

   ```python
   from pydantic import BaseModel

   class ToolResult(BaseModel):
       """Result schema for downstream parsing."""
       data: dict
       status: str

   def new_tool(param: str) -> ToolResult:
       """Tool implementation with explicit types."""
       # Implementation...
       return ToolResult(data={}, status="success")
   ```

2. **Enable in config** (`agents/<role>/config.yaml`):

   ```yaml
   tools:
     - name: new_tool
       enabled: true
   ```

3. **Document in prompt**: Update agent's `system_prompt` to describe tool usage

4. **Test**: Add unit test with mocked external calls

5. **Validate**: `make test-config`

### Modifying API Models

1. **Update Pydantic model** (`api/models/chat_models.py`):

   ```python
   from pydantic import BaseModel, Field

   class NewModel(BaseModel):
       """API model with validation."""
       field: str = Field(..., description="Field description")
       optional_field: str | None = None  # Use | not Optional
   ```

2. **Update server endpoint** (`server.py`)

3. **Update frontend types** (`src/frontend/src/lib/types.ts`)

4. **Test integration**: Run `make dev` and verify WebSocket events

5. **Document**: Update both AGENTS.md files

---

## Configuration Management

### Priority Hierarchy

1. **YAML files** - Canonical source of truth for behavior
2. **Environment variables** (`.env`) - Secrets and feature flags
3. **Python code** - Only wiring and factories

### Key Configuration Files

**Workflow Configuration** (`config/workflow.yaml`):

- Manager instructions and delegation rules
- Callback settings
- HITL approval configuration
- Checkpointing settings

**Agent Configuration** (`agents/<role>/config.yaml`):

- Model selection (per agent)
- System prompt
- Tool list with enabled/disabled flags
- Runtime parameters (temperature, max_tokens)

**Environment Variables** (`.env`):

```bash
# Required
OPENAI_API_KEY=sk-...
REDIS_URL=redis://...

# Optional
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4317
MEM0_HISTORY_DB_PATH=./var/mem0
```

**CRITICAL**: Run `make test-config` after ANY configuration change.

---

## Testing Patterns

### Configuration Validation

```bash
# ALWAYS run after YAML/config changes
make test-config
```

### Unit Tests

```bash
# Run specific test file
uv run pytest tests/test_workflow.py -v

# Run specific test
uv run pytest tests/test_workflow.py::test_workflow_creation -v

# Run tests matching pattern
uv run pytest -k "workflow" -v
```

### Integration Tests

```bash
# Run all tests (slow)
make test

# With coverage
uv run pytest --cov=src/agenticfleet --cov-report=term-missing
```

### Testing Rules

- Mock external LLM calls (patch `OpenAIResponsesClient`)
- Use `asyncio_mode=auto` (no `@pytest.mark.asyncio` needed)
- Prefer focused test invocations over full suite
- Coverage targets: core >80%, tools >70%, config 100%

---

## Code Quality Standards

### Type Hints

- **Required** on all functions: parameters and return types
- Use Python 3.12 syntax: `Type | None` (not `Optional[Type]`)
- No `Any` unless isolated adapter layer

```python
# Good
def process(data: str, optional: int | None = None) -> Result:
    ...

# Bad
def process(data, optional=None):  # Missing types
    ...

def process(data: str, optional: Optional[int] = None) -> Result:  # Use | not Optional
    ...
```

### Error Handling

Use custom exceptions from hierarchy:

```python
from agenticfleet.core.exceptions import (
    AgentConfigurationError,  # Config issues
    WorkflowError,            # Orchestration failures
    ToolExecutionError,       # Tool problems
    ContextProviderError      # Memory issues
)
```

### Logging

```python
from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)

# Use appropriate levels
logger.debug("Detailed debug info")
logger.info("Normal operation")
logger.warning("Warning condition")
logger.error("Error occurred", exc_info=True)
```

**Never** use `print()` in production code (only during debug, then remove).

### Code Style

- **Formatting**: Black (100 char lines) + Ruff
- **Imports**: Ruff auto-sorts (stdlib → third-party → local)
- **Docstrings**: Google style for public APIs

```bash
# Format code
make format

# Lint
make lint

# Type check
make type-check

# All checks
make check
```

---

## WebSocket Streaming

### Event Types

Events follow internal contract (converted from Microsoft Agent Framework):

```python
# Streaming text delta
{
    "type": "delta",
    "data": {"text": "partial content..."}
}

# Complete message
{
    "type": "message",
    "data": {"message": {"role": "assistant", "content": "..."}}
}

# Workflow complete
{
    "type": "complete",
    "data": {"result": "..."}
}

# Error
{
    "type": "error",
    "data": {"error": "Error message"}
}
```

### Adding New Event Types

1. Define in `api/models/sse_events.py`
2. Add handler in `api/event_collector.py`
3. Update `api/event_translator.py` if converting from framework events
4. Update frontend event parser
5. Document in both AGENTS.md files

---

## Redis State Management

**Client** (`api/redis_client.py`):

```python
class RedisClient:
    async def save_state(execution_id: str, state: ExecutionState)
    async def get_state(execution_id: str) -> ExecutionState | None
    async def update_status(execution_id: str, status: ExecutionStatus)
    async def delete_state(execution_id: str)
    async def list_executions(limit: int) -> list[str]
```

**Usage**:

- State persists for 3600s (1 hour) by default
- Keys: `agentic-fleet:execution:{execution_id}`
- Enables resumption and status polling

---

## Memory Integration

### Current Implementation

**Components**:

- `memory/context_provider.py` - Mem0 integration
- `memory/manager.py` - Memory lifecycle
- `memory/mcp_integration.py` - MCP server tools

**Status**: Exported but not wired into workflow prompts.

### Future Integration

To integrate memory into workflows:

1. Update manager instructions to reference memory
2. Extend workflow builder to inject context provider
3. Add memory retrieval in agent prompt preparation
4. Test with `tests/test_memory_system.py`

---

## Human-in-the-Loop (HITL)

### Approval Flow

```python
from agenticfleet.core.approval import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalDecision
)

# Create request
request = ApprovalRequest(
    operation_type="code_execution",
    description="Execute Python code",
    details={"code": "print('hello')"},
    timeout_seconds=300
)

# Request approval
response = await approval_handler.request_approval(request)

# Check decision
if response.decision == ApprovalDecision.APPROVE:
    # Execute operation
    ...
elif response.decision == ApprovalDecision.MODIFY:
    # Use modified data
    modified = response.modified_data
    ...
```

### Approval Configuration

**Workflow config** (`config/workflow.yaml`):

```yaml
human_in_the_loop:
  enabled: true
  approval_timeout_seconds: 300
  require_approval_for:
    - code_execution
    - file_operations
  trusted_operations:
    - web_search
    - data_analysis
```

---

## Observability

### OpenTelemetry

Enable tracing with environment variables:

```bash
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4317
ENABLE_SENSITIVE_DATA=false  # Don't capture prompts/completions
```

### Audit Logging

**Configuration** (`config/workflow.yaml`):

```yaml
audit_logging:
  enabled: true
  file_path: ./var/audit/audit.jsonl
  max_bytes: 10485760 # 10MB
  backup_count: 5
  redact_sensitive: true
```

**Event types**:

- `workflow.started`
- `approval.requested`
- `tool.called`
- `agent.spawned`
- `error.occurred`
- `state.changed`

---

## Common Pitfalls

| Issue                   | Cause               | Solution                                           |
| ----------------------- | ------------------- | -------------------------------------------------- |
| Agent config test fails | Missing YAML key    | Compare with working agent, run `make test-config` |
| Type errors in mypy     | Missing type hints  | Add explicit types to all function signatures      |
| Import errors           | Wrong module path   | Use absolute imports: `from agenticfleet.core...`  |
| Tool output not parsing | Schema mismatch     | Verify Pydantic model matches tool return type     |
| Workflow hangs          | Missing termination | Check manager instructions and max_round_count     |

---

## Before Committing

**Required checks**:

```bash
# 1. Configuration validation (CRITICAL)
make test-config

# 2. Code quality
make check

# 3. Tests
make test

# 4. Format
make format
```

---

## Quick Reference

```bash
# Package commands (use uv run prefix)
uv run python -m agenticfleet     # Run package
uv run pytest tests/              # Run tests
uv run mypy src/agenticfleet      # Type check

# Configuration
make test-config                  # Validate configs (CRITICAL)

# Quality
make check                        # Lint + type
make format                       # Auto-format

# Development
make backend                      # Backend only
make dev                          # Full stack
```

---

## References

- **Root guide**: `../../AGENTS.md`
- **Frontend guide**: `../frontend/AGENTS.md`
- **Architecture**: `../../docs/architecture/`
- **API docs**: Start server, visit <http://localhost:8000/docs>
- **Microsoft Agent Framework**: <https://github.com/microsoft/agent-framework>
