# API Reference

## Core Classes

### SupervisorWorkflow

Main workflow orchestrator combining DSPy and agent-framework.

#### Constructor

```python
SupervisorWorkflow(
    context: SupervisorContext,
    workflow_runner: Optional[Workflow] = None,
    dspy_supervisor: Optional[Any] = None,
    **kwargs
)
```

**Parameters**:

- `context`: Required SupervisorContext instance containing config, agents, and tools.
- `workflow_runner`: Optional Agent Framework Workflow instance.

**Attributes**:

- `context`: SupervisorContext instance
- `config`: WorkflowConfig instance
- `dspy_supervisor`: DSPySupervisor instance
- `agents`: Dictionary of ChatAgent instances
- `tool_registry`: ToolRegistry instance
- `history_manager`: HistoryManager instance

#### Methods

##### `async run(task: str) -> Dict[str, Any]`

Execute workflow for a given task (non-streaming).

**Parameters**:

- `task`: Task description string

**Returns**:

```python
{
    "result": str,          # Final execution result
    "routing": {            # Routing decision
        "mode": str,        # "parallel", "sequential", or "delegated"
        "assigned_to": List[str],
        "subtasks": List[str],
    },
    "quality": {            # Quality assessment
        "score": float,     # 0-10 scale
        "missing": str,     # Missing elements
        "improvements": str # Suggested improvements
    },
    "execution_summary": Dict[str, Any]
}
```

**Raises**:

- `ValueError`: If task is empty or too long
- `AgentExecutionError`: If agent execution fails
- `RoutingError`: If routing fails
- `HistoryError`: If history save fails

**Example**:

```python
from agentic_fleet.workflows.supervisor_workflow import create_supervisor_workflow

workflow = await create_supervisor_workflow(compile_dspy=True)
result = await workflow.run("Analyze the impact of AI")
print(f"Result: {result['result']}")
print(f"Quality: {result['quality']['score']}/10")
```

##### `async run_stream(task: str) -> AsyncIterator[Event]`

Execute workflow with streaming events.

**Parameters**:

- `task`: Task description string

**Yields**:

- `MagenticAgentMessageEvent`: Agent messages during execution
- `WorkflowOutputEvent`: Final result with complete data

**Example**:

```python
from agentic_fleet.workflows.supervisor_workflow import create_supervisor_workflow

workflow = await create_supervisor_workflow(compile_dspy=True)
async for event in workflow.run_stream("Your task"):
    if hasattr(event, 'agent_id'):
        print(f"{event.agent_id}: {event.message.text}")
    elif hasattr(event, 'data'):
        print(f"Final result: {event.data['result']}")
```

### WorkflowConfig

Configuration dataclass for workflow execution.

**Attributes**:

```python
max_rounds: int = 15                    # Max agent conversation turns
max_stalls: int = 3                     # Max stuck iterations
max_resets: int = 2                     # Max workflow resets
enable_streaming: bool = True           # Stream events
parallel_threshold: int = 3             # Min agents for parallel
dspy_model: str = "gpt-4.1"            # DSPy model
compile_dspy: bool = True               # Enable compilation
refinement_threshold: float = 8.0       # Quality threshold
enable_refinement: bool = True          # Auto-refine
enable_completion_storage: bool = False # OpenAI storage
agent_models: Optional[Dict[str, str]]  # Per-agent models
agent_temperatures: Optional[Dict[str, float]]  # Per-agent temps
history_format: str = "jsonl"           # "jsonl" or "json"
```

**Example**:

```python
from src.agentic_fleet.workflows.config import WorkflowConfig

config = WorkflowConfig(
    dspy_model="gpt-5-mini",
    refinement_threshold=9.0,
    max_rounds=20,
)
```

## DSPy Modules

### DSPySupervisor

DSPy module for intelligent task analysis and routing.

#### Methods

##### `analyze_task(task: str, use_tools: bool = False) -> Dict[str, Any]`

Analyze task complexity and requirements.

**Parameters**:

- `task`: Task to analyze
- `use_tools`: Whether to use tools during analysis

**Returns**:

```python
{
    "complexity": str,          # "simple", "moderate", "complex"
    "capabilities": List[str],  # Required capabilities
    "steps": int,              # Estimated steps
    "tool_requirements": List[str],  # Required tools
    "needs_web_search": bool   # Whether web search needed
}
```

##### `route_task(task: str, team: Dict[str, str]) -> Dict[str, Any]`

Route task to appropriate agents.

**Parameters**:

- `task`: Task to route
- `team`: Dictionary of agent names to descriptions

**Returns**:

```python
{
    "assigned_to": List[str],  # Agent names
    "mode": str,              # Execution mode
    "subtasks": List[str],    # Subtasks (if parallel)
    "tool_requirements": List[str]
}
```

##### `assess_quality(requirements: str, results: str) -> Dict[str, Any]`

Assess quality of execution results.

**Parameters**:

- `requirements`: Original task requirements
- `results`: Execution results

**Returns**:

```python
{
    "score": float,        # 0-10 scale
    "missing": str,        # Missing elements
    "improvements": str    # Suggested improvements
}
```

## Utility Classes

### ToolRegistry

Centralized registry for tool metadata and capabilities.

#### Methods

##### `register_tool(name: str, tool: ToolProtocol, agent: str, ...)`

Register a tool with metadata.

**Parameters**:

- `name`: Tool name
- `tool`: Tool instance
- `agent`: Agent name that has the tool
- `capabilities`: List of capability tags (optional)
- `use_cases`: List of use case descriptions (optional)

##### `get_tool_descriptions(agent_filter: Optional[str] = None) -> str`

Get formatted tool descriptions for DSPy prompts.

**Parameters**:

- `agent_filter`: Return only tools for this agent (optional)

**Returns**: Formatted string of tool descriptions

##### `get_agent_tools(agent_name: str) -> List[ToolMetadata]`

Get all tools available to a specific agent.

##### `get_tools_by_capability(capability: str) -> List[ToolMetadata]`

Find tools by capability tag.

**Example**:

```python
from src.agentic_fleet.utils.tool_registry import ToolRegistry

registry = ToolRegistry()
# Get all tools with web_search capability
search_tools = registry.get_tools_by_capability("web_search")
```

### HistoryManager

Manages execution history storage and retrieval.

#### Constructor

```python
HistoryManager(
    history_format: str = "jsonl",
    max_entries: Optional[int] = None
)
```

**Parameters**:

- `history_format`: "jsonl" or "json"
- `max_entries`: Maximum entries to keep (auto-rotation)

#### Methods

##### `save_execution(execution: Dict[str, Any]) -> str`

Save execution to history file.

**Returns**: Path to history file

**Raises**: `HistoryError` if save fails

##### `load_history(limit: Optional[int] = None) -> List[Dict[str, Any]]`

Load execution history.

**Parameters**:

- `limit`: Maximum entries to return (None for all)

**Returns**: List of execution dictionaries

##### `get_history_stats() -> Dict[str, Any]`

Get statistics about execution history.

**Returns**:

```python
{
    "total_executions": int,
    "total_time_seconds": float,
    "average_time_seconds": float,
    "average_quality_score": float,
    "format": str
}
```

##### `clear_history(keep_recent: int = 0)`

Clear execution history.

**Parameters**:

- `keep_recent`: Number of recent entries to keep (0 to clear all)

## Custom Exceptions

### WorkflowError

Base exception for all workflow errors.

### AgentExecutionError

Raised when agent execution fails.

**Attributes**:

- `agent_name`: Name of failed agent
- `task`: Task that failed
- `original_error`: Original exception

### RoutingError

Raised when routing fails or produces invalid results.

**Attributes**:

- `routing_decision`: The invalid routing decision (if available)

### ConfigurationError

Raised when configuration is invalid.

**Attributes**:

- `config_key`: Configuration key that failed (if available)

### HistoryError

Raised when history operations fail.

**Attributes**:

- `history_file`: Path to history file (if available)

## Factory Functions

### `create_supervisor_workflow(compile_dspy: bool = True) -> SupervisorWorkflow`

Factory function to create and initialize workflow.

**Parameters**:

- `compile_dspy`: Whether to compile DSPy module

**Returns**: Initialized SupervisorWorkflow instance

**Example**:

```python
from src.agentic_fleet.workflows.supervisor_workflow import create_supervisor_workflow

# With compilation
workflow = await create_supervisor_workflow(compile_dspy=True)

# Skip compilation for faster startup
workflow = await create_supervisor_workflow(compile_dspy=False)
```

## Configuration Utilities

### `load_config(config_path: Optional[str] = None) -> Dict[str, Any]`

Load configuration from YAML file.

**Parameters**:

- `config_path`: Path to config file (defaults to config/workflow_config.yaml)

**Returns**: Configuration dictionary

**Example**:

```python
from src.agentic_fleet.utils.config_loader import load_config

config = load_config()
```

### `validate_config(config_dict: Dict[str, Any]) -> WorkflowConfigSchema`

Validate configuration using Pydantic.

**Parameters**:

- `config_dict`: Configuration dictionary to validate

**Returns**: Validated WorkflowConfigSchema instance

**Raises**: `ConfigurationError` if invalid

**Example**:

```python
from src.agentic_fleet.utils.config_schema import validate_config
from src.agentic_fleet.workflows.exceptions import ConfigurationError

try:
    validated = validate_config(config_dict)
except ConfigurationError as e:
    print(f"Invalid config: {e}")
```

## Compiler Utilities

### `compile_supervisor(module, examples_path, use_cache) -> Any`

Compile DSPy supervisor module with training examples.

**Parameters**:

- `module`: DSPy module to compile
- `examples_path`: Path to training examples JSON
- `use_cache`: Whether to use/save cache

**Returns**: Compiled DSPy module

**Example**:

```python
from src.agentic_fleet.utils.compiler import compile_supervisor
from src.agentic_fleet.dspy_modules.supervisor import DSPySupervisor

supervisor = DSPySupervisor()
compiled = compile_supervisor(
    supervisor,
    examples_path="data/supervisor_examples.json",
    use_cache=True
)
```

### `clear_cache(cache_path: str = "logs/compiled_supervisor.pkl")`

Clear compiled module cache.

**Example**:

```python
from src.agentic_fleet.utils.compiler import clear_cache

clear_cache()
```

### `get_cache_info(cache_path: str = "logs/compiled_supervisor.pkl") -> Optional[Dict]`

Get cache metadata and statistics.

**Example**:

```python
from src.agentic_fleet.utils.compiler import get_cache_info

info = get_cache_info()
if info:
    print(f"Cache size: {info['cache_size_bytes']} bytes")
```

**Returns**:

```python
{
    "cache_path": str,
    "cache_size_bytes": int,
    "cache_mtime": str,
    "version": int,
    "examples_path": str,
    "created_at": str
}
```

## Type Hints

Key type definitions used throughout:

```python
from typing import Dict, Any, List, Optional, AsyncIterator
from src.agentic_fleet.utils.models import ExecutionMode, RoutingDecision

AgentDict = Dict[str, ChatAgent]
QualityAssessment = Dict[str, Any]
ExecutionResult = Dict[str, Any]
```

**Note**: `RoutingDecision` and `ExecutionMode` are defined in `src.agentic_fleet.utils.models`.

## Events

### MagenticAgentMessageEvent

Agent message during execution.

**Attributes**:

- `agent_id`: Agent identifier
- `message`: EventMessage with text content

### WorkflowOutputEvent

Final workflow result.

**Attributes**:

- `data`: Dictionary with result, routing, quality, execution_summary
- `source_executor_id`: Executor that generated the event

## Constants

```python
from src.agentic_fleet.utils.compiler import CACHE_VERSION

# CACHE_VERSION = 1  # Current cache version for invalidation
```

## REST API

The Agentic Fleet exposes a FastAPI-based REST API for interacting with the system.

### Base URL

`/api/v1/workflow`

### Endpoints

#### `POST /run`

Execute a workflow for a given task.

**Request Body**: `WorkflowRequest`

```json
{
  "task": "Your task description",
  "config": {
    "dspy_model": "gpt-4.1",
    "max_rounds": 10
  }
}
```

**Response**: `WorkflowResponse`

#### `POST /optimize`

Trigger a self-improvement/optimization run (background task).

**Request Body**: `OptimizationRequest`

```json
{
  "iterations": 3,
  "task": "Benchmark task",
  "compile_dspy": true
}
```

**Response**: `OptimizationResult` (pending status)

#### `GET /optimize/{job_id}`

Check status of an optimization run.

**Response**: `OptimizationResult`

#### `GET /history`

Retrieve execution history.

**Query Parameters**:

- `limit`: Number of entries (default: 20)
- `min_quality`: Minimum quality score filter (default: 0.0)

**Response**: `HistoryResponse`

#### `POST /self-improve`

Trigger self-improvement from history.

**Request Body**: `SelfImprovementRequest`

```json
{
  "min_quality": 8.0,
  "max_examples": 20
}
```

**Response**: `SelfImprovementResponse`

#### `GET /agents`

List available agents and their capabilities.

**Response**: `AgentListResponse`
