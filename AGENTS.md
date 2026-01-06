# AgenticFleet – Working Agreements

- **Purpose**: Quick, living guide for contributors. Update this file whenever workflows, tooling, or conventions change.

## Project Overview

AgenticFleet is a multi-agent orchestration system combining DSPy + Microsoft Agent Framework. Tasks flow through a 5-phase pipeline: **Analysis → Routing → Execution → Progress → Quality**. Supports delegated, sequential, parallel, handoff, and discussion execution modes.

**Current version highlights (v0.7.0)**:

- FastAPI-first architecture with services layer
- Typed DSPy Signatures with Pydantic validation
- DSPy Assertions for routing validation
- Routing Cache (TTL 5m) for latency reduction
- Smart Fast-Path for simple queries (<1s)
- Secure-by-default tracing (`capture_sensitive` defaults to false)
- Two-tier memory system (v0.8.0)

## Toolchain Defaults

- Shell: `zsh`.
- Python: `uv` (Python 3.12+, >0.8.0 mandatory). Never activate venvs manually; use `uv run ...`. Never use pip directly.
- Frontend: `npm` (Vite + React 19 + Tailwind). `bun` is _not_ used here.
- Type/lint: Ruff (formatter + lint), `ty` type checker, pytest for tests.

## First-Time Setup

- Install deps: `make install` (uv syncs all extras). Frontend deps: `make frontend-install`.
- Environment: copy `.env.example` → `.env`; set `OPENAI_API_KEY` (required) and optionally `TAVILY_API_KEY`, Cosmos settings, `DSPY_COMPILE`.
- Optional: `make pre-commit-install` to enable hooks.

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

## Architecture Overview (v0.7.0 FastAPI-First)

The codebase follows a **layered API → Services → Workflows → DSPy → Agents** architecture:

```
src/agentic_fleet/
├── api/              # FastAPI web layer
│   ├── api_v1/       # Versioned API
│   ├── events/       # Event mapping (workflow → UI)
│   └── routes/       # Route handlers (chat, workflow, nlu, dspy)
├── services/         # Async business logic (chat, workflow, optimization)
├── workflows/        # 5-phase orchestration pipeline
│   ├── executors/    # Phase executors (analysis, routing, execution, progress, quality)
│   ├── helpers/      # Workflow utilities
│   └── strategies/   # Execution modes (delegated/sequential/parallel)
├── dspy_modules/     # DSPy signatures, reasoner, GEPA optimization
│   ├── decisions/    # Decision-making modules
│   ├── gepa/         # GEPA optimization
│   └── lifecycle/    # Module lifecycle management
├── agents/           # Microsoft Agent Framework integration
├── tools/            # Tool adapters (Tavily, browser, MCP, code interpreter)
├── cli/              # Typer CLI
│   └── commands/     # CLI command handlers
├── models/           # Shared Pydantic schemas
├── evaluation/       # Batch evaluation and metrics
├── config/           # workflow_config.yaml (source of truth)
├── data/             # Training data (golden_dataset.json, supervisor_examples.json)
├── scripts/          # Utility scripts
└── utils/            # Infrastructure helpers
    ├── cfg/          # Configuration utilities
    ├── infra/        # Tracing, resilience, telemetry, logging
    └── storage/      # Cosmos, persistence, history management

src/frontend/         # React/Vite UI with React Query
```

**Config-Driven**: Models, agents, thresholds, and tools are declared in `src/agentic_fleet/config/workflow_config.yaml`. Reference YAML values—don't hardcode.

### 5-Phase Pipeline

1. **Analysis** (`AnalysisExecutor`): Extracts complexity, required capabilities, preferred tools
2. **Routing** (`RoutingExecutor`): Assigns agents, selects execution mode, creates subtasks
3. **Execution** (`ExecutionExecutor`): Runs agents via strategies (parallel/sequential/delegated)
4. **Progress** (`ProgressExecutor`): Evaluates completion (complete/refine/continue)
5. **Quality** (`QualityExecutor`): Scores output (0-10), identifies missing elements

**Fast-Path Optimization**: Simple queries (greetings, math, factual questions) bypass full pipeline via `is_simple_task()` check in `supervisor.py` (<1s response). Important: fast-path is intentionally **disabled on follow-up turns** so multi-turn context is not lost.

## Agents & Orchestration

- Stack: DSPy + Microsoft `agent-framework`. Agents live under `src/agentic_fleet/agents/`; orchestration in `src/agentic_fleet/workflows/`; DSPy reasoning in `src/agentic_fleet/dspy_modules/`.
- **Offline Layer (Production)**: DSPy compilation should be treated as **offline-only** via `agentic-fleet optimize` (cached under `.var/logs/compiled_supervisor.pkl`). Set `dspy.require_compiled: true` in `src/agentic_fleet/config/workflow_config.yaml` to fail-fast if artifacts are missing. Development can optionally start **background compilation** when enabled.
- **Dynamic Prompts**: Agent instructions (e.g., Planner) are generated dynamically via DSPy signatures (`PlannerInstructionSignature`) and optimized offline.
- **Services Layer**: `services/` provides async business logic layer bridging API routes to workflows:
  - `chat_service.py` — conversation management and agent routing
  - `chat_sse.py` / `chat_websocket.py` — real-time streaming
  - `workflow_service.py` — multi-agent orchestration entry point
  - `optimization_service.py` — GEPA optimization job management
- **Middleware**: `ChatMiddleware` handles cross-cutting concerns. `BridgeMiddleware` captures runtime history for offline learning.
- Routing/quality loops configured via `config/workflow_config.yaml`; history & tracing in `.var/logs/execution_history.jsonl`.
- **Group Chat**: Multi-agent discussions are supported via `DSPyGroupChatManager` and `GroupChatBuilder`. Workflows can participate as agents using the `workflow.as_agent()` pattern.
- **Latency Tips**: Clear DSPy cache after changes (`make clear-cache`), use `gpt-5-mini` for routing, disable judge if not needed.
- When adding or modifying agents/workflows, keep prompts/factories in sync and update config schema validation.

### Streaming & Events

- WebSocket/SSE streaming via `run_stream()` in `supervisor.py`
- Event types: `WorkflowStatusEvent`, `ExecutorCompletedEvent`, `MagenticAgentMessageEvent`, `ReasoningStreamEvent`
- Event mapping: `api/events/mapping.py` routes events to UI components

**Adding new events**: When adding streaming event types:

1. Update backend mapping in `src/agentic_fleet/api/events/mapping.py`
2. Add `ui_routing:` entry in `workflow_config.yaml`
3. Update frontend types in `src/frontend/src/api/types.ts`
4. Handle in `src/frontend/src/stores/chatStore.ts`

### HITL + Resume (agent-framework semantics)

- The backend can surface **request events** during streaming; the client can respond with `workflow.response` messages to unblock execution.
- Checkpointing for new runs is enabled via an opt-in flag (e.g. `enable_checkpointing`), which configures checkpoint storage.
- Resuming is explicit: `{"type": "workflow.resume", "checkpoint_id": "..."}`.
- `checkpoint_id` is **resume-only** (message XOR checkpoint_id). Never send a start message and `checkpoint_id` together.

### DSPy Integration

- **Compilation is offline-first**—production should be **offline-only** (via `scripts/optimize_reasoner.py` / `agentic-fleet optimize`) and fail-fast when artifacts are missing.
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

### NLU Module

- Intent classification and entity extraction
- DSPy-backed: `dspy_modules/nlu.py`
- API endpoints: `api/routes/nlu.py`
- Update signatures and compiled caches together when changing NLU behaviour

## Frontend (React/TypeScript)

```
src/frontend/src/
├── api/          # API client + React Query (server state)
│   ├── QueryProvider.tsx  # React Query provider
│   ├── hooks.ts       # Custom API hooks (useChat, useWorkflow, etc.)
│   ├── http.ts        # HTTP client (axios-based)
│   ├── websocket.ts   # WebSocket client for streaming
│   └── config.ts      # API configuration
├── components/   # Reusable UI organized by domain
│   ├── ui/      # shadcn/ui design system primitives
│   ├── chat/    # Chat interface (messages, input, container)
│   ├── message/ # Message rendering (markdown, code, reasoning)
│   ├── workflow/# Workflow visualization
│   ├── dashboard/# Dashboard components
│   └── layout/  # Layout shells (headers, sidebars, panels)
├── pages/        # Page-level views (composition & orchestration)
│   ├── chat-page.tsx      # Main chat interface
│   └── dashboard-page.tsx # Optimization dashboard
├── stores/       # Zustand stores (client state, UI preferences)
├── hooks/        # Custom React hooks
├── lib/          # Utility functions
├── contexts/     # React contexts
├── styles/       # CSS organization
├── root/         # App shell and view routing
│   └── app.tsx
└── main.tsx      # Entry point
```

**Component Organization Rules:**

1. UI Primitives (`components/ui/`): shadcn/ui only, no business logic
2. Domain Components (`components/[domain]/`): Reusable UI for specific domains
   - Chat: All chat interface components including PromptInput
   - Message: Message rendering and formatting
   - Workflow: Workflow visualization components
   - Layout: App structure (headers, sidebars, panels)
3. Pages (`pages/`): Top-level views that compose components and manage view-level state
4. Hooks always in `hooks/` directory (never in `components/`)
5. Organize by technical concern, not features

**Import Patterns:**

```typescript
// Pages
import { ChatPage } from "@/pages/chat-page";

// Domain components
import { ChatMessages, PromptInput } from "@/components/chat";
import { Message, Markdown } from "@/components/message";

// UI primitives
import { Button, Sidebar } from "@/components/ui";

// Hooks, stores
import { useSidebar, useIsMobile } from "@/hooks";
import { useChatStore } from "@/stores";
```

- API calls: Always through `api/hooks.ts` (never direct fetch)
- State: Server state via React Query, client state via Zustand stores
- Config: `VITE_API_URL` in `.env` (defaults to `http://localhost:8000`)
- Package manager: `npm` only (not bun)
- Testing: Vitest with jsdom, React Testing Library

## Memory System (v0.8.0)

A two-tier memory architecture enabling agents to learn, remember, and improve over time.

### Quick Start

1. **Read core context**: `.fleet/context/core/project.md`, `human.md`, `persona.md`
2. **Use commands**: `/init`, `/learn`, `/recall`, `/reflect` (Claude Code)
3. **Search memory**: `uv run python .fleet/context/scripts/memory_manager.py recall "query"`

### Memory Commands

| Command    | Description                   | Usage                           |
| ---------- | ----------------------------- | ------------------------------- |
| `/init`    | Initialize memory system      | Run once on setup               |
| `/learn`   | Index a skill to Chroma       | After creating a skill          |
| `/recall`  | Semantic search in memory     | When looking for past solutions |
| `/reflect` | Consolidate session learnings | At end of session               |

### Memory Hierarchy

```
.fleet/context/
├── core/           # Always in-context (project, human, persona)
├── blocks/         # Topic-scoped (commands, architecture, gotchas)
├── skills/         # Learned patterns (indexed to Chroma)
├── system/         # Agent skill definitions
└── .chroma/        # Chroma Cloud config
```

### Block Format

All memory blocks use frontmatter:

```yaml
---
label: block-name
description: What this block contains
limit: 5000
scope: core|project|workflows|decisions
updated: 2024-12-29
---
```

### Integration

- **Claude Code**: Symlinks in `.claude/skills/` → `.fleet/context/system/`
- **OpenCode**: Configured in `opencode.jsonc` (context + skills paths)
- **Chroma Cloud**: Semantic search via `.fleet/context/.chroma/config.yaml`

See `.fleet/context/SKILL.md` for full documentation.

## Common Tasks

### Adding an Agent

1. Add config to `workflow_config.yaml` under `agents:`
2. Add prompts to `src/agentic_fleet/agents/prompts.py` (referenced as `prompts.<name>`)
3. Tools auto-resolve via `ToolRegistry`; list tool names in YAML

### Adding a Tool

1. Create adapter in `src/agentic_fleet/tools/` (extend base patterns)
2. Add to agent's `tools:` list in workflow_config.yaml (auto-discovered)

### Modifying Workflow Phases

- Executors: `workflows/executors/` (AnalysisExecutor, RoutingExecutor, etc.)
- Strategies: `workflows/strategies/` (delegated/sequential/parallel)
- Models: `models/` (workflow data models and events)

### Testing

**Backend (pytest)**:

```bash
make test                           # All backend tests
make test-config                    # Config validation
uv run pytest tests/path/test_foo.py::test_bar  # Single test
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

## Conventions & Notes

- Keep code typed; follow Ruff/ty defaults (line length 100, py312 syntax, docstrings for public APIs).
- Python 3.12+ with modern syntax (`type | None`, not `Optional[type]`)
- Strict typing with `ty` checker; avoid `Any`
- Absolute imports: `from agentic_fleet.utils import ...`
- Avoid committing artifacts from `.var/` (logs, caches, compiled DSPy outputs).
- Prefer `make` targets over raw commands; if adding new workflows/tests, add a Make target and update this file.
- Chat conversations persist to `.var/data/conversations.json` by default (override with `CONVERSATIONS_PATH`); delete the file to reset local chat history.
- If you change how to start, test, or observe the system, append the updated commands here and, for larger shifts, create an ExecPlan entry in `docs/plans/current.md`.

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

## CI/CD

GitHub Actions workflows ensure code quality and test coverage:

**Main Pipeline (`.github/workflows/ci.yml`)**:

- **Quality Job**: Unified job running lint (Ruff), type-check (`ty`), and security scan (Bandit) in parallel
- **Test Job**: Matrix testing (Python 3.12/3.13, Linux/macOS)
- **Frontend Job**: Vitest unit tests
- **Build Job**: Verifies buildability (depends on quality, test, frontend)

**Auxiliary Workflows**:

- `codeql.yml` - Security analysis (weekly schedule + manual)
- `dependency-review.yml` - Dependency checks (manual, non-blocking)
- `docs-sync.aw.md` - Documentation generation (manual)

**Note**: PR triggers removed from auxiliary workflows. Use `workflow_dispatch` to run manually.

## Files to Read First

1. `src/agentic_fleet/config/workflow_config.yaml` — All runtime settings
2. `src/agentic_fleet/workflows/supervisor.py` — Main orchestration entry
3. `src/agentic_fleet/agents/coordinator.py` — AgentFactory (creates agents from YAML)
4. `src/agentic_fleet/dspy_modules/reasoner.py` — DSPy module manager
5. `src/agentic_fleet/api/events/mapping.py` — Event routing (maps workflow events → UI)

## Git Hooks

Enhanced git hooks enforce quality standards and automation:

### Available Hooks

| Hook                 | Purpose                                       | Command to install   |
| -------------------- | --------------------------------------------- | -------------------- |
| `pre-commit`         | Run linting, type checking, config validation | `make hooks-install` |
| `pre-push`           | Prevent committing .var/ files, run tests     | `make hooks-install` |
| `prepare-commit-msg` | Auto-prefix commits with scope                | `make hooks-install` |
| `post-checkout`      | Sync dependencies on branch switch            | `make hooks-install` |

### Installation

```bash
# Install all hooks (pre-commit framework + enhanced hooks)
make setup-hooks

# Install enhanced hooks only
make hooks-install

# Update hooks to latest version
make hooks-update

# Remove enhanced hooks
make hooks-uninstall
```

### What Hooks Do

1. **Pre-commit Hook**:
   - Validates `.env` file (prevents empty API keys)
   - Checks `workflow_config.yaml` syntax
   - Warns about DSPy compilation issues
   - Prevents committing `.var/` directory files
   - Runs `make check` for quick quality validation

2. **Pre-push Hook**:
   - Validates Git LFS configuration
   - Prevents pushing `.var/` files
   - Prevents pushing compiled DSPy cache (`.pkl`)
   - Checks workflow config structure
   - Optionally runs fast tests

3. **Prepare-commit-msg Hook**:
   - Auto-prefixes commits with scope (`backend:`, `frontend:`, `dspy:`, etc.)
   - Suggests emoji based on changed files
   - Maintains conventional commit format

4. **Post-checkout Hook**:
   - Detects dependency changes (`uv.lock`, `package.json`)
   - Offers to sync dependencies automatically
   - Detects DSPy signature changes
   - Offers to clear DSPy cache
   - Shows helpful next steps after checkout

### Factory Hooks Configuration

Factory hooks provide AI-assisted automation for common development tasks. Configuration in `.factory/hooks.yaml`:

```yaml
hooks:
  - name: validate-config
    description: Validate workflow config before changes
    trigger: before-file-change
    pattern: src/agentic_fleet/config/workflow_config.yaml
    command: make test-config

  - name: clear-dspy-cache
    description: Clear DSPy cache when signatures change
    trigger: after-file-change
    pattern: src/agentic_fleet/dspy_modules/signatures.py
    command: make clear-cache

  - name: validate-imports
    description: Validate Python imports
    trigger: before-file-change
    pattern: "**/*.py"
    exclude: "**/tests/**"
    command: uv run ruff check --select=I --fix .
```

See `.factory/hooks.yaml` for complete configuration.

## Additional Resources

- **DSPy Documentation**: https://dspy.ai
- **Agent Framework**: https://github.com/microsoft/agent-framework
- **Contributing Guide**: See `CONTRIBUTING.md` for detailed guidelines
- **Troubleshooting**: See `docs/users/troubleshooting.md`
