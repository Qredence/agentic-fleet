# Project Context: AgenticFleet

## Overview

**AgenticFleet** is a production-ready multi-agent orchestration system combining DSPy + Microsoft Agent Framework. It automatically routes tasks to specialized AI agents through a **5-phase pipeline** (Analysis → Routing → Execution → Progress → Quality).

| Attribute       | Value                             |
| --------------- | --------------------------------- |
| Version         | 0.6.98                            |
| Python          | 3.12+ / 3.13                      |
| License         | MIT                               |
| Package Manager | uv (Python), npm (Frontend)       |
| Repository      | github.com/Qredence/agentic-fleet |

## Architecture

### Layered Structure

```
src/agentic_fleet/
├── api/              # FastAPI web layer
│   ├── api_v1/       # Versioned API
│   ├── events/       # Event mapping (workflow → UI)
│   └── routes/       # Route handlers (chat, workflow, nlu, dspy, observability)
├── services/         # Async business logic
│   ├── chat_sse.py / chat_websocket.py  # Real-time streaming
│   ├── optimization_service.py          # GEPA optimization jobs
│   └── dspy_service.py                   # DSPy program management
├── workflows/        # 5-phase orchestration pipeline
│   ├── supervisor.py # Main entry point (1520 lines)
│   ├── executors/    # Phase executors
│   ├── strategies/   # Execution modes (delegated/sequential/parallel/discussion)
│   └── helpers/      # Fast-path, routing, quality utilities
├── dspy_modules/     # DSPy intelligence layer
│   ├── reasoner.py   # DSPyReasoner (orchestrates all DSPy modules)
│   ├── signatures.py # Typed signatures with Pydantic outputs
│   ├── typed_models.py # Pydantic output models
│   └── gepa/         # GEPA optimization
├── agents/           # Microsoft Agent Framework integration
│   ├── coordinator.py # AgentFactory (creates ChatAgent from YAML)
│   └── base.py       # DSPyEnhancedAgent wrapper
├── tools/            # Tool adapters
│   ├── tavily_tool.py, browser_tool.py, mcp_tools.py
│   └── hosted_code_adapter.py
├── models/           # Shared Pydantic schemas
├── config/           # workflow_config.yaml (source of truth)
├── cli/              # Typer CLI (agentic-fleet command)
└── utils/            # Infrastructure (cfg/, infra/, storage/)
```

### Frontend Structure

```
src/frontend/src/
├── api/              # React Query + HTTP/WebSocket clients
├── features/         # Feature modules (chat, dashboard, layout, workflow)
├── components/       # Reusable UI (ui/ for shadcn primitives)
├── hooks/            # Custom React hooks
├── lib/              # Utility functions
└── tests/            # Vitest + React Testing Library
```

## Five-Phase Pipeline

1. **Analysis** (`AnalysisExecutor`): DSPy extracts task complexity, required capabilities, tool recommendations
2. **Routing** (`RoutingExecutor`): Selects agents, execution mode, creates subtasks, generates tool plan
3. **Execution** (`ExecutionExecutor`): Runs agents via strategies (parallel/sequential/delegated)
4. **Progress** (`ProgressEvaluator`): Evaluates completion status, decides if refinement needed
5. **Quality** (`QualityExecutor`): Scores output 0-10, identifies gaps, suggests improvements

**Fast-Path**: Simple queries bypass pipeline via `is_simple_task()` check (<1s response). Disabled on follow-up turns.

## Agent Configuration

Agents defined in `workflow_config.yaml`:

| Agent              | Model         | Tools                                    | Purpose                                   |
| ------------------ | ------------- | ---------------------------------------- | ----------------------------------------- |
| researcher         | gpt-4.1-mini  | TavilySearchTool                         | Web research                              |
| analyst            | gpt-5.1-codex | HostedCodeInterpreterTool                | Data analysis                             |
| writer             | gpt-5.1-chat  | -                                        | Content creation                          |
| planner            | gpt-5-mini    | -                                        | Task orchestration (DSPy dynamic prompts) |
| coder              | gpt-5-mini    | HostedCodeInterpreterTool                | Code generation                           |
| copilot_researcher | gpt-5-mini    | PackageSearch, Context7, Tavily, Browser | Enhanced research                         |
| documentation      | gpt-5-mini    | -                                        | Documentation generation                  |

## DSPy Integration

### Typed Signatures (Pydantic)

All DSPy signatures use Pydantic models for structured outputs:

```python
class TaskRouting(dspy.Signature):
    task: str = dspy.InputField(desc="The task to route")
    team: str = dspy.InputField(desc="Description of available agents")
    decision: RoutingDecisionOutput = dspy.OutputField()  # Pydantic model
```

### Key DSPy Features

- **Routing Cache**: TTL 5 minutes, max 1024 entries
- **GEPA Optimization**: Offline prompt tuning (`agentic-fleet optimize`)
- **Dynamic Prompts**: Planner uses `PlannerInstructionSignature` for context-aware instructions
- **Compiled Artifacts**: `.var/cache/dspy/compiled_reasoner.json`

### Configuration

```yaml
dspy:
  model: gpt-5-mini
  routing_model: gpt-5-mini
  use_typed_signatures: true
  enable_routing_cache: true
  require_compiled: false # Set true in production
```

## Development Commands

| Task              | Command                                     |
| ----------------- | ------------------------------------------- |
| Install deps      | `make install`                              |
| Dev servers       | `make dev` (backend :8000 + frontend :5173) |
| Tests             | `make test` / `make test-fast`              |
| Frontend tests    | `make test-frontend`                        |
| Lint + type check | `make check`                                |
| Full QA           | `make qa`                                   |
| Format            | `make format`                               |
| Clear DSPy cache  | `make clear-cache`                          |
| Optimize          | `agentic-fleet optimize`                    |
| CLI run           | `agentic-fleet run -m "task"`               |

## CLI Entry Points

Three aliases available:

- `agentic-fleet`
- `agenticfleet`
- `fleet`

## Key Files

| File                          | Purpose                                  |
| ----------------------------- | ---------------------------------------- |
| `workflows/supervisor.py`     | Main orchestration entry point           |
| `agents/coordinator.py`       | AgentFactory - creates agents from YAML  |
| `dspy_modules/reasoner.py`    | DSPyReasoner - orchestrates DSPy modules |
| `config/workflow_config.yaml` | All runtime settings                     |
| `api/events/mapping.py`       | Event routing (workflow → UI)            |

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

## CI/CD

- **Pre-commit**: Ruff (lint + format), Prettier, end-of-file-fixer
- **CI**: `ci.yml` - tests, type checking, linting
- **Agentic Workflows**: `ci-doctor.md`, `q.md`, `docs-sync.aw.md`
- **Release**: `release.yml` - automated releases

## Test Status

- **Backend**: 635 passed, 3 failed (tracing tests need update)
- **Frontend**: Vitest with jsdom, React Testing Library
- **E2E**: Playwright (requires dev servers)

## Dependencies

Core dependencies:

- `agent-framework==1.0.0b251223` (Microsoft Agent Framework)
- `dspy` (DSPy for prompt optimization)
- `fastapi[standard]>=0.120.1`
- `azure-*` packages for Azure integration
- `langfuse` for observability

## Environment Variables

**Required**: `OPENAI_API_KEY`

**Optional**:

- `TAVILY_API_KEY` (web search)
- `DSPY_COMPILE=false` (skip recompilation)
- `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` (Azure OpenAI)
- `AGENTICFLEET_USE_COSMOS=true` (Cosmos DB integration)
