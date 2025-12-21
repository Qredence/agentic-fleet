# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgenticFleet is a multi-agent orchestration system combining DSPy + Microsoft Agent Framework. Tasks flow through a 5-phase pipeline: **Analysis → Routing → Execution → Progress → Quality**. Supports delegated, sequential, parallel, handoff, and discussion execution modes.

**Current version highlights (v0.7.0 – FastAPI-First Architecture)**:

- **Layered Architecture**: API → Services → Workflows → DSPy → Agents
- Typed DSPy Signatures with Pydantic validation
- DSPy Assertions for routing validation
- Routing Cache (TTL 5m) for latency reduction
- Smart Fast-Path for simple queries (<1s)
- Secure-by-default tracing (`capture_sensitive` defaults to false)
- Services layer for async business logic

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
├── api/                      # FASTAPI WEB LAYER
│   ├── deps.py               # Dependency injection (DB sessions, Auth, Clients)
│   ├── lifespan.py           # Startup/Shutdown events (e.g., initializing DSPy)
│   ├── middleware.py         # FastAPI-level middleware (CORS, Auth, Logging)
│   ├── main.py               # FastAPI app entry + router mounting
│   ├── routes/               # Primary API endpoints
│   │   ├── chat.py           # Chat and streaming agent interactions
│   │   ├── optimization.py   # GEPA/DSPy optimization job management
│   │   ├── workflows.py      # Workflow status and management
│   │   └── nlu.py            # Intent classification + entity extraction
│   └── v1/events/            # Versioned event mapping
│       └── mapping.py        # Event routing (maps workflow events → UI)
│
├── services/                 # ASYNC BUSINESS LOGIC LAYER
│   ├── agent_service.py      # Factory for creating and managing agents
│   ├── chat_service.py       # Manages conversation logic and agent routing
│   ├── chat_sse.py           # Logic for Server-Sent Events (SSE) streaming
│   ├── chat_websocket.py     # Logic for real-time WebSocket communication
│   ├── optimization_service.py # Bridges API to GEPA optimization loops
│   └── workflow_service.py   # Orchestrates complex multi-agent workflows
│
├── workflows/                # THE ORCHESTRATION LAYER (5-Phase Pipeline)
│   ├── supervisor.py         # Main entry point + fast-path detection
│   ├── executors.py          # 5 executors (Analysis, Routing, Execution, Progress, Quality)
│   ├── strategies.py         # Execution modes (delegated/sequential/parallel)
│   ├── builder.py            # Graph construction for Agent Framework
│   ├── context.py            # SupervisorContext for state management
│   ├── handoff.py            # Structured agent handoff management
│   ├── models.py             # Workflow data models and events
│   ├── narrator.py           # DSPy-based event narration for UX messages
│   └── initialization.py     # Bootstraps contexts, agent catalogs, caches
│
├── dspy_modules/             # THE INTELLIGENCE LAYER (DSPy + GEPA)
│   ├── reasoner.py           # DSPyReasoner (manages all DSPy modules)
│   ├── signatures.py         # DSPy signatures for all phases
│   ├── typed_models.py       # Pydantic models for structured outputs
│   ├── assertions.py         # DSPy assertions for validation
│   ├── nlu.py                # Intent classification + entity extraction
│   ├── optimizer.py          # GEPA loop for reflective prompt evolution
│   └── refinement.py         # BestOfN and iterative improvement
│
├── agents/                   # THE RUNTIME LAYER (MS Agent Framework)
│   ├── coordinator.py        # AgentFactory (creates agents from YAML)
│   ├── base.py               # DSPyEnhancedAgent mixin
│   ├── foundry.py            # Azure AI Foundry integration
│   └── prompts.py            # Centralized prompt modules
│
├── tools/                    # THE CAPABILITY LAYER
│   ├── tavily_tool.py        # Tavily search integration
│   ├── browser_tool.py       # Browser automation for page capture
│   ├── mcp_tools.py          # MCP tool bridges
│   └── hosted_code_adapter.py # Hosted code interpreter
│
├── utils/                    # THE INFRASTRUCTURE LAYER
│   ├── cfg/                  # Configuration loading
│   ├── infra/                # Tracing, resilience, telemetry, logging
│   └── storage/              # Cosmos, persistence, history management
│
├── models/                   # SHARED DATA MODELS (Pydantic)
│   ├── conversations.py      # Persistence-ready conversation models
│   ├── requests.py           # API Request schemas
│   ├── responses.py          # API Response schemas
│   └── workflows.py          # Workflow-specific models
│
├── evaluation/               # BATCH EVALUATION
│   ├── evaluator.py          # Evaluation engine
│   └── metrics.py            # Evaluation metrics
│
└── config/                   # SYSTEM CONFIGURATION
    └── workflow_config.yaml  # Source of truth for models, tools, thresholds
```

**Config-Driven**: Models, agents, thresholds, and tools are declared in `src/agentic_fleet/config/workflow_config.yaml`. Reference YAML values—don't hardcode.

### Layered Architecture Flow

```
┌──────────┐     ┌─────────────────────────────────────────────────────┐
│   User   │────▶│                  API LAYER                         │
│ (WS/SSE) │     │  routes/chat.py → middleware.py → deps.py          │
└──────────┘     └─────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVICES LAYER                                │
│  chat_service.py → chat_websocket.py / chat_sse.py                  │
│  workflow_service.py ← optimization_service.py                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    WORKFLOWS LAYER (5-Phase Pipeline)                │
│  ┌─────────┐  ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌─────────┐│
│  │ANALYSIS │→ │ ROUTING │→ │ EXECUTION │→ │ PROGRESS │→ │ QUALITY ││
│  └─────────┘  └─────────┘  └───────────┘  └──────────┘  └─────────┘│
│       ↓            ↓              ↓             ↓            ↓      │
│    DSPy NLU    DSPy Route   Agent Framework  Event Stream  Assert  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              ┌──────────┐   ┌──────────┐    ┌──────────┐
              │ DSPy     │   │ Agents   │    │  Tools   │
              │ Modules  │   │ (AF)     │    │          │
              └──────────┘   └──────────┘    └──────────┘
```

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
- Event mapping: `api/v1/events/mapping.py` routes events to UI components

**Adding new events**: When adding streaming event types:

1. Update backend mapping in `src/agentic_fleet/api/v1/events/mapping.py`
2. Add `ui_routing:` entry in `workflow_config.yaml`
3. Update frontend types in `src/frontend/src/api/types.ts`
4. Handle in `src/frontend/src/features/chat/stores/chatStore.ts`

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

### Services Layer (New in v0.7.0)

The services layer provides **async business logic** between API routes and the workflow orchestration:

- **`chat_service.py`**: Conversation management, agent routing decisions
- **`chat_sse.py`**: Server-Sent Events streaming implementation
- **`chat_websocket.py`**: Real-time WebSocket for bidirectional communication
- **`workflow_service.py`**: Entry point for multi-agent workflow orchestration
- **`optimization_service.py`**: Bridges API to GEPA optimization loops

**Key principle**: Long-running agentic tasks are async—services ensure FastAPI remains responsive while agents think.

### DSPy Integration

- **Compilation is offline-first**—production should be **offline-only** (via `scripts/optimize_reasoner.py` / `agentic-fleet optimize`) and fail-fast when artifacts are missing by setting `dspy.require_compiled: true` in `src/agentic_fleet/config/workflow_config.yaml`. Development may optionally start **background compilation** when enabled (see `initialize_workflow_context(..., compile_dspy=True)`).
- Signatures: `src/agentic_fleet/dspy_modules/signatures.py`
- Cache: `.var/logs/compiled_supervisor.pkl`
- Clear cache after modifying DSPy modules: `make clear-cache`
- Examples: `src/agentic_fleet/data/supervisor_examples.json`
- **Typed Signatures (v0.6.9+)**: All outputs use Pydantic models (`typed_models.py`)
- **Assertions (v0.6.9+)**: Routing validation via `dspy.Assert` and `dspy.Suggest` (`assertions.py`)
- **Routing Cache (v0.6.9+)**: Cached decisions (TTL 5m) in `reasoner.py`
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
├── api/          # API client + React Query (server state)
├── features/     # Feature-based organization
│   ├── chat/     # Chat interface (UI + store + streaming)
│   └── dashboard/# Optimization dashboard
├── components/   # Reusable UI organized by domain
│   └── ui/       # shadcn/ui design system primitives
├── hooks/        # Custom React hooks
├── lib/          # Utility functions
├── contexts/     # React contexts
├── styles/       # CSS organization
└── main.tsx      # Entry point
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
- Models: `workflows/models.py` (workflow data models and events)

### Adding API Endpoints

1. Create route in `src/agentic_fleet/api/routes/`
2. Add business logic to `src/agentic_fleet/services/`
3. Register route in `api/main.py`
4. Add request/response models to `models/requests.py` / `models/responses.py`

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

- Generic TTL cache in `utils/cache.py` with hit rate tracking
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
- Location: `src/agentic_fleet/api/middleware.py`

### NLU Module

- Intent classification and entity extraction
- DSPy-backed: `dspy_modules/nlu.py`
- API endpoints: `api/routes/nlu.py`
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
- `ENABLE_SENSITIVE_DATA=true` (capture prompts in traces/telemetry; default: false)
- `LOG_JSON=0` (human-readable logs; JSON on by default)
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` (Azure OpenAI)
- `AZURE_AI_SEARCH_ENDPOINT`, `AZURE_COSMOS_ENDPOINT` (Azure services)
- `AGENTICFLEET_USE_COSMOS=true` (enable Azure Cosmos DB integration)
- `AGENTICFLEET_DEFAULT_USER_ID=user123` (default user ID for multi-tenant scoping)

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
- **Tracing**: Start Jaeger UI with `make tracing-start`, view at <http://localhost:16686>

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
3. `src/agentic_fleet/services/workflow_service.py` — Service layer entry point
4. `src/agentic_fleet/agents/coordinator.py` — AgentFactory (creates agents from YAML)
5. `src/agentic_fleet/dspy_modules/reasoner.py` — DSPy module manager
6. `src/agentic_fleet/api/v1/events/mapping.py` — Event routing (maps workflow events → UI)
7. `AGENTS.md` (root) — Toolchain defaults and working agreements
8. `.github/copilot-instructions.md` — Additional AI assistant context

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

- **DSPy Documentation**: https://dspy.ai
- **Agent Framework**: https://github.com/microsoft/agent-framework
- **Contributing Guide**: See `CONTRIBUTING.md` for detailed guidelines
- **Troubleshooting**: See `docs/users/troubleshooting.md`
