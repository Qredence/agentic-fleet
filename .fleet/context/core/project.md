# Project Context: AgenticFleet

## Architecture Overview

AgenticFleet is a production-ready **multi-agent orchestration system** combining DSPy + Microsoft Agent Framework. It automatically routes tasks to specialized AI agents through a **5-phase pipeline** (Analysis → Routing → Execution → Progress → Quality).

### Layered Architecture

```
src/agentic_fleet/
├── api/              # FastAPI web layer (routes, middleware, deps)
│   ├── api_v1/       # Versioned API
│   ├── events/       # Event mapping (workflow → UI)
│   └── routes/       # Route handlers (chat, workflow, nlu, dspy)
├── services/         # Async business logic (chat, workflow, optimization)
├── workflows/        # 5-phase orchestration pipeline
│   ├── supervisor.py # Main entry point with fast-path detection
│   ├── executors/    # Phase executors (Analysis, Routing, Execution, Progress, Quality)
│   ├── strategies/   # Execution modes (delegated/sequential/parallel/handoff/discussion)
│   └── helpers/      # Utilities (is_simple_task, context management)
├── dspy_modules/     # DSPy intelligence layer
│   ├── reasoner.py   # DSPyReasoner (orchestrates all DSPy modules)
│   ├── signatures.py # Typed signatures (TaskAnalysis, TaskRouting, QualityAssessment)
│   ├── typed_models.py # Pydantic output models for structured outputs
│   ├── assertions.py # DSPy Assert/Suggest for routing validation
│   ├── reasoner_modules.py # Module management and initialization
│   └── gepa/         # GEPA optimization (automatic prompt tuning)
├── agents/           # Microsoft Agent Framework integration
│   ├── coordinator.py # AgentFactory (creates ChatAgent from YAML config)
│   ├── base.py       # DSPyEnhancedAgent (wraps ChatAgent with DSPy reasoning)
│   └── prompts.py    # Static agent prompts
├── tools/            # Tool adapters
│   ├── tavily_tool.py    # Web search
│   ├── hosted_code_adapter.py # Code interpreter
│   ├── mcp_adapter.py     # MCP tools
│   └── base.py           # SchemaToolMixin, ToolProtocol
├── models/           # Shared Pydantic schemas
├── config/           # workflow_config.yaml (source of truth)
├── data/             # Training data (golden_dataset.json, supervisor_examples.json)
├── utils/            # Organized into subpackages
│   ├── cfg/          # Configuration loading
│   ├── infra/        # Tracing, resilience, telemetry, logging
│   └── storage/      # Cosmos DB, history, persistence
└── cli/              # Typer CLI commands
```

## Five-Phase Pipeline

Every task flows through intelligent orchestration:

1. **Analysis** (`AnalysisExecutor`): DSPy extracts task complexity (low/medium/high), required capabilities, and tool recommendations
2. **Routing** (`RoutingExecutor`): Selects agents, execution mode, creates subtasks, generates tool plan
3. **Execution** (`ExecutionExecutor`): Runs agents via strategies (delegated/sequential/parallel/handoff/discussion)
4. **Progress** (`ProgressEvaluator`): Evaluates completion status, decides if refinement needed
5. **Quality** (`QualityExecutor`): Scores output 0-10, identifies gaps, suggests improvements

**Fast-Path**: Simple queries (greetings, math, factual) bypass pipeline via `is_simple_task()` check in `supervisor.py` (<1s response). Disabled on follow-up turns to preserve history.

## DSPy Integration

### Typed Signatures with Pydantic (v0.6.9+)

All DSPy signatures use Pydantic models for structured outputs via `dspy.TypedPredictor`:

```python
# signatures.py
class TaskRouting(dspy.Signature):
    task: str = dspy.InputField(desc="The task to route")
    team: str = dspy.InputField(desc="Description of available agents")
    context: str = dspy.InputField(desc="Optional execution context")

    decision: RoutingDecisionOutput = dspy.OutputField(
        desc="Structured routing decision with agents, mode, subtasks, and tools"
    )

# typed_models.py
class RoutingDecisionOutput(BaseModel):
    assigned_to: list[str] = Field(min_length=1)
    execution_mode: Literal["delegated", "sequential", "parallel"]
    subtasks: list[str] = Field(default_factory=list)
    tool_requirements: list[str] = Field(default_factory=list)
    tool_plan: list[str] = Field(default_factory=list)
    reasoning: str = Field(description="Reasoning for the routing decision")
```

### DSPy Assertions for Validation

Routing validation via `dspy.Assert` (hard constraint) and `dspy.Suggest` (soft guidance):

```python
# assertions.py
def validate_agent_exists(assigned_agents, available_agents) -> bool:
    """Check all assigned agents exist in available pool."""
    Assert(len(assigned_agents) > 0, "Must assign at least one agent")
    for agent in assigned_agents:
        Assert(agent.lower() in [a.lower() for a in available_agents],
               f"Agent {agent} not in available pool")
```

### Routing Cache (v0.6.9+)

Cached routing decisions with TTL (5 minutes) to reduce LLM calls:

```python
# reasoner.py
self._routing_cache = RoutingCache(ttl_seconds=300, max_size=1024)
```

### GEPA Optimization

Offline prompt optimization via GEPA (Genetic Prompt Algorithm):

```bash
agentic-fleet optimize  # Runs GEPA optimization
# Outputs: .var/cache/dspy/compiled_reasoner.json
```

Configuration in `workflow_config.yaml`:

```yaml
dspy:
  require_compiled: false # Set true in production
  use_typed_signatures: true
  enable_routing_cache: true
  routing_cache_ttl_seconds: 300
```

## Microsoft Agent Framework Integration

### ChatAgent Creation via AgentFactory

Agents created from YAML config using `AgentFactory`:

```python
# coordinator.py
class AgentFactory:
    def create_agent(self, name: str, agent_config: dict) -> ChatAgent:
        # Supports local agents, Azure Foundry agents
        # Dynamic prompt generation via DSPy (PlannerInstructionSignature)
        # Tool resolution via ToolRegistry
```

### DSPy-Enhanced Agents

`DSPyEnhancedAgent` wraps `ChatAgent` with DSPy reasoning strategies:

```python
# base.py
class DSPyEnhancedAgent(ChatAgent):
    def __init__(self, enable_dspy: bool = True,
                 reasoning_strategy: str = "chain_of_thought"):
        # ReAct: tool-augmented reasoning
        # ProgramOfThought: code-like reasoning
        # ChainOfThought: standard CoT
```

### Workflow and Checkpointing

Uses agent-framework Workflow for orchestration with checkpoint storage:

```python
# supervisor.py
from agent_framework._workflows import (
    WorkflowStartedEvent, WorkflowStatusEvent, WorkflowOutputEvent,
    ExecutorCompletedEvent, RequestInfoEvent,  # HITL support
    FileCheckpointStorage, InMemoryCheckpointStorage
)
```

### Agent Handoffs

Direct agent-to-agent transfers supported:

```python
# strategies.py
execute_sequential_with_handoffs()  # Sequential with handoffs
format_handoff_input()              # Format context transfer
HandoffManager                      # Manage handoff flow
```

## Key Technologies

| Technology          | Role                                  | Version/Pattern          |
| ------------------- | ------------------------------------- | ------------------------ |
| **DSPy**            | Prompt optimization, typed signatures | 3.x with TypedPredictor  |
| **Agent Framework** | ChatAgent, Workflow, Thread           | Microsoft Magentic Fleet |
| **FastAPI**         | HTTP/WebSocket server                 | 0.115+                   |
| **React 19**        | Frontend                              | Vite + Tailwind          |
| **Pydantic**        | Type validation                       | 2.x                      |
| **ChromaDB**        | Semantic memory                       | Memory system            |
| **OpenTelemetry**   | Tracing                               | Jaeger, Langfuse         |
| **Azure**           | Cosmos DB, AI Foundry                 | Optional                 |

## Development Commands

```bash
make install           # Python deps via uv
make dev               # Backend :8000 + Frontend :5173
make test              # Pytest
make check             # Ruff + ty type-check
make format            # Ruff formatting
make clear-cache       # Clear DSPy cache
agentic-fleet optimize # GEPA optimization
agentic-fleet run -m "task"  # CLI task execution
```

## Configuration

All runtime settings in `src/agentic_fleet/config/workflow_config.yaml`:

- DSPy models, routing cache, typed signatures
- Agent configurations (model, tools, instructions)
- Workflow phases (timeouts, thresholds, max rounds)
- Execution strategies (parallel threshold, timeout)
- Quality assessment (thresholds, judge model)

## Runtime Data

```
.var/
├── cache/dspy/        # Compiled reasoner cache
├── logs/
│   ├── compiled_supervisor.pkl
│   ├── execution_history.jsonl
│   └── gepa/          # GEPA optimization logs
├── data/
│   └── conversations.json
└── checkpoints/       # Workflow checkpoints
```

## Conventions

- Python 3.12+ with modern syntax (`type | None`, not `Optional[type]`)
- Absolute imports: `from agentic_fleet.utils import ...`
- Ruff formatter (line length 100), ty type checker
- Pydantic models for all DSPy outputs
- Config-driven (reference `workflow_config.yaml`, don't hardcode)
- Conventional commits format
- uv for Python, npm for frontend (not bun)
