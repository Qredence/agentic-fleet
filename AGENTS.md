# AgenticFleet – Working Agreements

- **Purpose**: Quick, living guide for contributors. Update this file whenever workflows, tooling, or conventions change.

## Toolchain Defaults

- Shell: `zsh`.
- Python: `uv` (Python 3.12+). Never activate venvs manually; use `uv run ...`.
- Frontend: `npm` (Vite + React 19 + Tailwind). `bun` is _not_ used here.
- Type/lint: Ruff (formatter + lint), `ty` type checker, pytest for tests.

## First-Time Setup

- Install deps: `make install` (uv syncs all extras). Frontend deps: `make frontend-install`.
- Environment: copy `.env.example` → `.env`; set `OPENAI_API_KEY` (required) and optionally `TAVILY_API_KEY`, Cosmos settings, `DSPY_COMPILE`.
- Optional: `make pre-commit-install` to enable hooks.

## Run & Develop

- Backend CLI: `make run` (`agentic-fleet` Typer console).
- Dev servers: `make dev` (backend on :8000, frontend on :5173). Backend only: `make backend`. Frontend only: `make frontend-dev`. Build UI: `make build-frontend`.
- Config: tune models/agents in `config/workflow_config.yaml`; runtime data (caches, logs, history) lives under `.var/`.

## Testing & Quality

- Full suite: `make test` (pytest -v).
- Config smoke: `make test-config` (validates workflow configs).
- Frontend tests: `make test-frontend`; E2E: `make test-e2e` (requires dev servers; install Playwright browsers with `npx playwright install chromium`).
- Lint/format: `make lint`, `make format`; type-check: `make type-check`; quick all-in-one: `make check`.

## Architecture Overview (v0.7.0 FastAPI-First)

The codebase follows a **layered API → Services → Workflows → DSPy → Agents** architecture:

```
src/agentic_fleet/
├── api/              # FastAPI web layer (routes, middleware, deps)
├── services/         # Async business logic (chat, workflow, optimization)
├── workflows/        # 5-phase orchestration pipeline
├── dspy_modules/     # DSPy signatures, reasoner, GEPA optimization
├── agents/           # Microsoft Agent Framework integration
├── tools/            # Tool adapters (Tavily, browser, MCP)
├── utils/            # Infrastructure (cfg/, infra/, storage/)
├── models/           # Shared Pydantic schemas
├── evaluation/       # Batch evaluation and metrics
└── config/           # workflow_config.yaml (source of truth)
```

## Agents & Orchestration

- Stack: DSPy + Microsoft `agent-framework`. Agents live under `src/agentic_fleet/agents/`; orchestration in `src/agentic_fleet/workflows/`; DSPy reasoning in `src/agentic_fleet/dspy_modules/`.
- **5-Phase Pipeline** (v0.6.6): `analysis → routing → execution → progress → quality`. Judge phase removed for ~66% latency reduction.
- **Smart Fast-Path** (v0.6.7): Simple tasks (factual questions, math, greetings) bypass multi-agent routing via `is_simple_task()` and get direct LLM responses in <1 second.
  - Important: fast-path is intentionally **disabled on follow-up turns** (when a conversation thread already has history) so multi-turn context is not lost.
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
- **Streaming/Event surface**: Workflow events are mapped through `agentic_fleet.api.events.mapping` to UI-friendly categories (reasoning, routing, analysis, quality, agent output). Keep SSE payloads and frontend workflow renderers in sync when adding new event kinds.
- **HITL + Resume (agent-framework semantics)**:
  - The backend can surface **request events** during streaming; the client can respond with `workflow.response` messages to unblock execution.
  - Checkpointing for new runs is enabled via an opt-in flag (e.g. `enable_checkpointing`), which configures checkpoint storage.
  - Resuming is explicit and uses a `workflow.resume` message containing `checkpoint_id`.
  - `checkpoint_id` is **resume-only** (message XOR checkpoint_id). Never send a start message and `checkpoint_id` together.
- **NLU module**: A DSPy-backed NLU stack (`dspy_modules/nlu.py`, `api/routes/nlu.py`) exposes intent classification and entity extraction endpoints. Update signatures and compiled caches together when changing NLU behaviour.
- **Typed Signatures & Assertions** (v0.6.9): All DSPy outputs now use Pydantic models (`dspy_modules/typed_models.py`) for strict validation. Routing decisions are guarded by `dspy.Assert` and `dspy.Suggest` in `dspy_modules/assertions.py`.
- **Routing Cache**: Routing decisions are cached (TTL 5m) to reduce latency and cost. Configure via `enable_routing_cache` in `workflow_config.yaml`.
- For multi-agent expansion with OpenAI Agents SDK, treat Codex CLI as an MCP server and mirror roles from `.github/agents/agent-framework-spec.md`; document new roles/prompts here and in `docs/` as needed.

## Conventions & Notes

- Keep code typed; follow Ruff/ty defaults (line length 100, py312 syntax, docstrings for public APIs).
- Avoid committing artifacts from `.var/` (logs, caches, compiled DSPy outputs).
- Prefer `make` targets over raw commands; if adding new workflows/tests, add a Make target and update this file.
- Chat conversations persist to `.var/data/conversations.json` by default (override with `CONVERSATIONS_PATH`); delete the file to reset local chat history.
- Structured logging: JSON logs are **on by default**. Set `LOG_JSON=0` to use human-readable logs instead.
- If you change how to start, test, or observe the system, append the updated commands here and, for larger shifts, create an ExecPlan entry in `docs/plans/current.md`.
