# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgenticFleet is a multi-agent orchestration system combining DSPy + Microsoft Agent Framework. Tasks flow through a 5-phase pipeline: **Analysis → Routing → Execution → Progress → Quality**. Supports delegated, sequential, parallel, handoff, and discussion execution modes.

**Current version highlights (v0.6.9)**:

- Typed DSPy Signatures with Pydantic validation
- DSPy Assertions for routing validation
- Routing Cache (TTL 5m) for latency reduction
- Smart Fast-Path for simple queries (<1s)

## Development Commands

| Task                 | Command                                             |
| -------------------- | --------------------------------------------------- |
| Install dependencies | `make install` (uses uv)                            |
| Full-stack dev       | `make dev` (backend :8000, frontend :5173)          |
| Backend only         | `make backend`                                      |
| Frontend only        | `make frontend-dev`                                 |
| Run tests            | `make test`                                         |
| Run single test      | `uv run pytest tests/path/test_file.py::test_name`  |
| Frontend tests       | `make test-frontend` (Vitest)                       |
| E2E tests            | `make test-e2e` (Playwright, requires dev servers)  |
| All tests            | `make test-all`                                     |
| Lint + type check    | `make check` (fast, run before commits)             |
| Full QA suite        | `make qa` (lint + format + type + all tests)        |
| Format code          | `make format`                                       |
| Frontend lint        | `make frontend-lint`                                |
| Clear DSPy cache     | `make clear-cache` (after modifying DSPy modules)   |
| Evaluate history     | `make evaluate-history` (DSPy-based evaluation)     |
| Start tracing        | `make tracing-start` (Jaeger UI at :16686)          |
| Stop tracing         | `make tracing-stop`                                 |
| CLI task             | `agentic-fleet run -m "your task" --verbose`        |
| CLI evaluate         | `agentic-fleet eval` (run evaluations with tracing) |
| CLI optimize         | `agentic-fleet optimize` (DSPy optimization)        |
| CLI inspect          | `agentic-fleet inspect` (workflow inspection)       |
| CLI dev server       | `agentic-fleet dev` (start development server)      |

**Package managers**: `uv` for Python (mandatory, >0.8.0; never pip directly), `npm` for frontend (not bun).

**Pre-commit hooks**: Available via `make pre-commit-install` (Ruff, Prettier, type-check).

## Architecture

```
src/agentic_fleet/
├── agents/           # Agent definitions, AgentFactory (coordinator.py)
├── workflows/        # Orchestration: supervisor.py (entry), executors.py (phases)
│   ├── supervisor.py # Main workflow entry + fast-path detection
│   ├── executors.py  # 5 executors (Analysis, Routing, Execution, Progress, Quality)
│   ├── strategies.py # Execution modes (delegated/sequential/parallel)
│   ├── streaming_events.py # SSE event streaming
│   └── narrator.py   # DSPy-based event narration for user-friendly messages
├── dspy_modules/     # DSPy signatures, reasoner, typed models, assertions
│   ├── reasoner.py   # DSPyReasoner (manages all DSPy modules)
│   ├── signatures.py # DSPy signatures for all phases
│   ├── typed_models.py # Pydantic models for structured outputs
│   └── assertions.py # DSPy assertions for validation
├── tools/            # Tool adapters (Tavily, browser, MCP, code interpreter)
├── app/              # FastAPI backend + SSE streaming
│   ├── main.py       # FastAPI app entry
│   └── routers/      # API routes (chat, workflow, nlu, dspy_management)
├── config/           # workflow_config.yaml - source of truth for all settings
├── core/             # Middleware (ChatMiddleware, BridgeMiddleware)
├── data/             # Training data (golden_dataset.json, supervisor_examples.json)
└── utils/            # Shared helpers, organized into submodules
    ├── infra/        # Tracing, resilience, telemetry, logging
    ├── storage/      # Cosmos, persistence, history management
    └── cfg/          # Configuration utilities
src/frontend/         # React/Vite UI with React Query
```

**Config-Driven**: Models, agents, thresholds, and tools are declared in `src/agentic_fleet/config/workflow_config.yaml`. Reference YAML values—don't hardcode.

### 5-Phase Pipeline

1. **Analysis** (`AnalysisExecutor`): Extracts complexity, required capabilities, preferred tools
2. **Routing** (`RoutingExecutor`): Assigns agents, selects execution mode, creates subtasks
3. **Execution** (`ExecutionExecutor`): Runs agents via strategies (parallel/sequential/delegated)
4. **Progress** (`ProgressExecutor`): Evaluates completion (complete/refine/continue)
5. **Quality** (`QualityExecutor`): Scores output (0-10), identifies missing elements

**Fast-Path Optimization**: Simple queries (greetings, math, factual questions) bypass full pipeline via `is_simple_task()` check in `supervisor.py` (<1s response).

### Streaming & Events

- WebSocket/SSE streaming via `run_stream()` in `supervisor.py`
- Event types: `WorkflowStatusEvent`, `ExecutorCompletedEvent`, `MagenticAgentMessageEvent`, `ReasoningStreamEvent`
- Event mapping: `api/events/mapping.py` routes events to UI components

**Human-in-the-loop + resume protocol (WebSocket)**:

- During streaming, the backend may emit request events that require a client response.
- Clients can reply with `{"type": "workflow.response", ...}` to unblock the workflow.
- Checkpointing is enabled for new runs by configuring checkpoint storage (opt-in flag), not by sending `checkpoint_id`.
- Resuming is explicit: `{"type": "workflow.resume", "checkpoint_id": "..."}`.
- `checkpoint_id` is **resume-only** (message XOR checkpoint_id).

## Key Conventions

### Python

- Python 3.12+ with modern syntax (`type | None`, not `Optional[type]`)
- Strict typing with `ty` checker; avoid `Any`
- Absolute imports: `from agentic_fleet.utils import ...`
- Line length: 100 chars (Ruff enforced)
- Run quality checks before commits: `make check`
- Pre-commit hooks available: `make pre-commit-install`

### DSPy Integration

- **Compilation is offline only**—never compile at runtime (via `scripts/optimize_reasoner.py`)
- Signatures: `src/agentic_fleet/dspy_modules/signatures.py`
- Cache: `.var/logs/compiled_supervisor.pkl`
- Clear cache after modifying DSPy modules: `make clear-cache`
- Examples: `src/agentic_fleet/data/supervisor_examples.json`
- **Typed Signatures (v0.6.9)**: All outputs use Pydantic models (`typed_models.py`)
- **Assertions (v0.6.9)**: Routing validation via `dspy.Assert` and `dspy.Suggest` (`assertions.py`)
- **Routing Cache (v0.6.9)**: Cached decisions (TTL 5m) in `reasoner.py`
- **Management API**: Runtime inspection via `/dspy/*` endpoints (`api/routes/dspy.py`)
  - `GET /dspy/prompts` - List all DSPy prompts
  - `GET /dspy/config` - Get DSPy configuration
  - `GET /dspy/stats` - Get execution statistics
  - `GET /dspy/cache` - Cache info
  - `DELETE /dspy/cache` - Clear DSPy cache
  - `GET /dspy/reasoner/summary` - Get reasoner summary
  - `DELETE /dspy/reasoner/routing-cache` - Clear routing cache
  - `GET /dspy/signatures` - List DSPy signatures

### Frontend (React/TypeScript)

```
src/frontend/src/
├── api/               # API layer (React Query integration)
│   ├── QueryProvider.tsx  # React Query provider
│   ├── hooks.ts       # Custom API hooks (useChat, useWorkflow, etc.)
│   ├── http.ts        # HTTP client (axios-based)
│   ├── websocket.ts   # WebSocket client for streaming
│   └── config.ts      # API configuration
├── features/          # Feature modules (chat, workflow, etc.)
├── stores/            # State management (Zustand)
└── components/
    ├── layout/        # Layout components (Sidebar, Header)
    └── ui/            # UI atoms (shadcn/ui)
```

- API calls: Always through `api/hooks.ts` (never direct fetch)
- State: Server state via React Query, client state via Zustand stores
- Config: `VITE_API_URL` in `.env` (defaults to `http://localhost:8000`)
- Package manager: `npm` only (not bun)
- Testing: Vitest with jsdom, React Testing Library

## Common Tasks

### Adding an Agent

1. Add config to `workflow_config.yaml` under `agents:`
2. Add prompts to `src/agentic_fleet/agents/prompts.py` (referenced as `prompts.<name>`)
3. Tools auto-resolve via `ToolRegistry`; list tool names in YAML

### Adding a Tool

1. Create adapter in `src/agentic_fleet/tools/` (extend base patterns)
2. Add to agent's `tools:` list in workflow_config.yaml (auto-discovered)

### Modifying Workflow Phases

- Executors: `workflows/executors.py` (AnalysisExecutor, RoutingExecutor, etc.)
- Strategies: `workflows/strategies.py` (delegated/sequential/parallel)
- Streaming: `workflows/execution/streaming_events.py`

### Testing

**Backend (pytest)**:

```bash
make test                           # All backend tests
make test-config                    # Config validation
uv run pytest tests/unit/test_foo.py::test_bar  # Single test
```

**Frontend (Vitest)**:

```bash
make test-frontend                  # Unit tests
cd src/frontend && npm run test:ui  # Interactive UI
```

**E2E (Playwright)**:

```bash
make test-e2e                       # Requires dev servers running
npx playwright install chromium     # Install browser (first time)
```

## Performance & Optimization

### Smart Fast-Path (v0.6.7)

- Detects simple tasks via `is_simple_task()` in `supervisor.py`
- Bypasses multi-agent routing for greetings, math, factual questions
- Response time: <1 second
- Configure thresholds in `workflow_config.yaml`

### Routing Cache (v0.6.9)

- Caches routing decisions for 5 minutes (TTL configurable)
- Enable via `enable_routing_cache: true` in `workflow_config.yaml`
- Reduces latency and API costs for repeated tasks

### Latency Tips

- Use `gpt-5-mini` for routing (fast, cheap)
- Reduce `gepa_max_metric_calls` in config
- Disable judge phase if quality threshold not needed
- Clear DSPy cache after changes: `make clear-cache`

### GEPA Optimization

- Offline optimization via `scripts/optimize_reasoner.py`
- Logs: `.var/logs/gepa/`
- Metrics: routing accuracy, latency, quality scores

### TTL Cache

- Generic TTL cache in `utils/cache_impl.py` with hit rate tracking
- Agent response caching decorator for expensive operations
- Cosmos DB mirroring for distributed caching

## Advanced Features

### Group Chat Mode

- Multi-agent discussions via `DSPyGroupChatManager`
- Speaker selection: `GroupChatSpeakerSelection` signature
- Workflows can participate as agents: `workflow.as_agent()`

### Middleware System

- **ChatMiddleware**: Cross-cutting concerns (logging, tracing)
- **BridgeMiddleware**: Captures runtime history for offline learning
- Location: `src/agentic_fleet/core/middleware.py`

### NLU Module

- Intent classification and entity extraction
- DSPy-backed: `dspy_modules/nlu.py`
- API endpoints: `app/routers/nlu.py`
- Update signatures and compiled caches together

### Dynamic Prompts

- Agent instructions generated via DSPy signatures
- `PlannerInstructionSignature` for optimized prompts
- Offline optimization via GEPA

### Event Narrator

- DSPy-based module that translates raw workflow events to user-friendly narratives
- Location: `workflows/narrator.py`
- Uses `WorkflowNarration` signature for context-aware message generation
- Integrates with streaming events system for real-time UI updates

## Environment Variables

**Required**: `OPENAI_API_KEY`

**Optional**:

- `TAVILY_API_KEY` (web search)
- `DSPY_COMPILE=false` (skip recompilation)
- `ENABLE_OTEL=true` + `OTLP_ENDPOINT` (tracing)
- `LOG_JSON=0` (human-readable logs; JSON on by default)
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` (Azure OpenAI)
- `AZURE_AI_SEARCH_ENDPOINT`, `AZURE_COSMOS_ENDPOINT` (Azure services)

Copy `.env.example` → `.env` for local development.

## Runtime Data

All caches, logs, and history live under `.var/` (gitignored). Key locations:

```
.var/
├── cache/dspy/             # DSPy module cache
├── logs/
│   ├── compiled_supervisor.pkl  # Main DSPy compiled cache
│   ├── execution_history.jsonl  # Workflow decisions & results
│   ├── gepa/                    # GEPA optimization logs
│   └── evaluation/              # Evaluation results
└── data/
    ├── conversations.json       # Chat history
    └── db/                      # SQLite databases

src/agentic_fleet/data/
├── golden_dataset.json     # Training data for DSPy optimization
└── supervisor_examples.json # Supervisor examples for few-shot learning
```

Initialize: `make init-var`

## Debugging Tips

- **Routing issues**: Check `.var/logs/execution_history.jsonl` for decisions
- **Slow workflows**: Reduce `gepa_max_metric_calls` in workflow_config.yaml, or use `--fast` flag
- **DSPy fallback**: If no compiled cache, system uses zero-shot (set `require_compiled: true` in production)
- **Frontend not connecting**: Verify `VITE_API_URL` matches backend port
- **Type errors**: Run `make type-check` to catch issues before runtime
- **Tracing**: Start Jaeger UI with `make tracing-start`, view at http://localhost:16686

## Common Pitfalls

1. **Never compile DSPy at runtime** - Compilation is strictly offline via `scripts/optimize_reasoner.py`
2. **Clear cache after DSPy changes** - Run `make clear-cache` after modifying signatures or reasoner
3. **Don't hardcode config values** - Always reference `workflow_config.yaml`
4. **Set `require_compiled: true` in production** - Ensures compiled cache exists before execution
5. **Use uv, not pip** - Direct pip usage breaks dependency management (uv >0.8.0 mandatory)
6. **Frontend uses npm, not bun** - Project standardized on npm for consistency
7. **Update typed models with signatures** - Pydantic models in `typed_models.py` must match DSPy outputs
8. **Structured logging is JSON by default** - Set `LOG_JSON=0` for human-readable logs
9. **Do not send `checkpoint_id` with a start message** - In agent-framework, `checkpoint_id` is resume-only (message XOR checkpoint_id)
10. **Fast-path is stateless** - It should only apply to first-turn/simple prompts; follow-up turns must use the full workflow to preserve history

## Files to Read First

1. `src/agentic_fleet/config/workflow_config.yaml` — All runtime settings
2. `src/agentic_fleet/workflows/supervisor.py` — Main orchestration entry
3. `src/agentic_fleet/agents/coordinator.py` — AgentFactory (creates agents from YAML)
4. `src/agentic_fleet/dspy_modules/reasoner.py` — DSPy module manager
5. `AGENTS.md` (root) — Toolchain defaults and working agreements

## Deployment

### Docker

```bash
cd docker && docker compose up    # Start all services
docker compose up --build         # Rebuild and start
```

Configuration in `docker/` directory with Dockerfile and compose configurations.

### Azure

Azure Bicep templates and deployment scripts in `infrastructure/azure/standard-agent-setup/`:

```bash
cd infrastructure/azure/standard-agent-setup
./deploy.sh                       # Deploy to Azure
```

Deploys: App Service, Cosmos DB, Azure OpenAI, Key Vault, and supporting resources.

## Additional Resources

- **DSPy Documentation**: https://dspy-docs.vercel.app/
- **Agent Framework**: https://github.com/microsoft/agent-framework
- **Contributing Guide**: See `CONTRIBUTING.md` for detailed guidelines
- **Troubleshooting**: See `docs/users/troubleshooting.md`
