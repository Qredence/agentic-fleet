## AgenticFleet — AI Coding Agent Guide

### Architecture Overview

**Multi-tier stack**: FastAPI backend (`src/agentic_fleet/`) orchestrates Microsoft Agent Framework Magentic workflows; React + Vite frontend (`src/frontend/src`) consumes streaming SSE events from `/v1/responses`.

**Data flow**: User message → WorkflowFactory → MagenticFleetWorkflow → agent specialists (planner → executor → coder → verifier → generator) → WorkflowEventBridge → ResponseAggregator → SSE stream → chatStore (Zustand) → UI.

**Agent roster**: Five specialists coordinate via manager-orchestrated turns. Each agent has a `get_config()` factory under `src/agentic_fleet/agents/{planner,executor,coder,verifier,generator}.py`, configured declaratively in `config/workflows.yaml`.

**YAML-driven workflows**: `config/workflows.yaml` defines manager settings (model, reasoning effort, max rounds), agent roster, and tool wiring. Never hardcode model IDs or prompts in Python/TypeScript—extend the YAML or `prompts/*.py` modules instead.

### Essential Commands

**All Python commands must use `uv run`** (respects uv-managed deps):

- `make install` — Sync Python deps from `uv.lock`
- `make frontend-install` — Install npm packages in `src/frontend`
- `make dev` — Launch backend (8000) + frontend (5173) with hot reload
- `make backend` — Backend only (uvicorn on 8000)
- `make frontend-dev` — Frontend only (Vite on 5173)
- `make check` — Lint (ruff), format (black), type-check (mypy), tests
- `make test-config` — Validate YAML wiring via WorkflowFactory
- `make validate-agents` — Ensure AGENTS.md files are synchronized
- `uv run pytest tests/test_*.py -k <pattern>` — Focused test runs

**Config override**: Set `AF_WORKFLOW_CONFIG=/abs/path/to/custom.yaml` to use non-default workflows.

### Critical Development Patterns

**Event streaming architecture**: `workflow/events.WorkflowEventBridge` converts Microsoft Agent Framework events (MagenticAgentDeltaEvent, MagenticOrchestratorMessageEvent) into JSON-safe dictionaries. `api/responses/service.ResponseAggregator` wraps these into OpenAI Responses-compatible SSE payloads. Frontend parsers in `lib/parsers/` and `stores/chatStore.ts` reconstruct messages with agent IDs, reasoning content, and chain-of-thought metadata.

**Agent factory pattern**: `agents/coordinator.AgentFactory.create_agent()` instantiates ChatAgent from config dicts. Tool references resolve via `ToolRegistry` (from `tools/registry.py`). New agents require:

1. Module in `src/agentic_fleet/agents/<role>.py` with `get_config() -> dict`
2. Entry in `config/workflows.yaml` under `workflows.<id>.agents.<role>`
3. Export in `agents/__init__.py`
4. Coverage in `tests/test_workflow_factory.py`

**Checkpointing**: Persistent state writes to `var/checkpoints/`; wire via `MagenticFleetBuilder.with_checkpointing(True)`.

**Human-in-the-loop**: Approval gates route through `api/approvals/routes.py` and `core/approval.py`. Set `human_in_the_loop: true` in YAML for sensitive actions.

### Change Map

| Change Type              | Files to Update                                                                         | Notes                                                           |
| ------------------------ | --------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| **Orchestration limits** | `config/workflows.yaml` → `max_round_count`, `max_stall_count`, `temperature`           | Mirrored in packaged `src/agentic_fleet/workflows.yaml`         |
| **Agent behavior**       | `agents/<role>.py` (`get_config()`), `agents/__init__.py`, `config/workflows.yaml`      | Keep prompt strings in `prompts/<role>.py` modules              |
| **Event/SSE schema**     | `workflow/events.py`, `api/responses/service.py`, `lib/parsers/`, `stores/chatStore.ts` | Test in `tests/test_api_responses_streaming.py`                 |
| **UI components**        | `src/frontend/src/components/chat/`, `components/ui/`                                   | Sync types with `types/chat.ts` and `src/agentic_fleet/models/` |
| **Tools**                | `tools/registry.py`, `agents/<role>.py` (tools list)                                    | Return Pydantic models; mock in tests                           |
| **API routes**           | `api/<domain>/routes.py`, `api/app.py` (router registration)                            | Update OpenAPI schemas in `models/`                             |

### Conventions (Non-Negotiable)

- **No hardcoded config**: Model IDs, prompts, tool lists live in YAML/`prompts/` modules, not Python/TS sources.
- **uv prefix**: Always `uv run <python-command>` for pytest, ruff, black, mypy, uvicorn—direct invocations skip uv-managed env.
- **Frontend commands from `src/frontend/`**: `cd src/frontend && npm run {test,lint,build}`.
- **Documentation chain**: Any change to agent roster or workflows requires updates to root `AGENTS.md`, `src/agentic_fleet/AGENTS.md`, `src/frontend/AGENTS.md`, `tests/AGENTS.md`. Run `make validate-agents` before committing.
- **Tests mock network**: Never call real OpenAI/Mem0 inside `tests/`. Use fixtures or stubs.
- **Secrets in `.env`**: Never commit API keys or credentials. Load from `.env` (ignored) or env vars.

### Testing Strategy

- **Backend unit**: `uv run pytest -v` (or `make test`). Focus on `test_workflow_factory.py`, `test_event_bridge.py`, `test_api_responses_streaming.py`.
- **Frontend unit**: `cd src/frontend && npm test` (Vitest).
- **E2E**: `make dev` (launch stack), then `make test-e2e` (Playwright).
- **Config validation**: `make test-config` instantiates WorkflowFactory to catch YAML/import errors.
- **Coverage**: `uv run pytest --cov=src/agentic_fleet --cov-report=term-missing`.

### Environment Variables

**Required**: `OPENAI_API_KEY` (in `.env` or env).
**Optional**: `OPENAI_BASE_URL`, `AF_WORKFLOW_CONFIG`, `ENABLE_OTEL`, `OTLP_ENDPOINT`, `MEM0_HISTORY_DB_PATH`. Document new vars in `docs/configuration-guide.md`.

### Common Troubleshooting

- **"OPENAI_API_KEY is not set"**: Ensure `.env` exists and loads before backend starts.
- **Workflow not found**: Verify ID in resolved YAML (`make test-config`), check `/v1/entities` response.
- **Hanging SSE**: Inspect `ResponseAggregator` logic, run `tests/test_api_responses_streaming.py`, check browser console for SSE errors.
- **Missing static assets**: Rerun `make build-frontend` to refresh `src/agentic_fleet/ui`.
- **Import errors**: Run `uv sync` to align lockfile with `pyproject.toml`.

### Key Files Reference

- **Backend entry**: `src/agentic_fleet/server.py` (ASGI app), `api/app.py` (FastAPI factory)
- **Workflow builder**: `workflow/magentic_builder.py`, `workflow/magentic_workflow.py`
- **Event bridge**: `workflow/events.py` → `api/responses/service.py` → SSE
- **Agent factory**: `agents/coordinator.AgentFactory`
- **Frontend store**: `src/frontend/src/stores/chatStore.ts` (Zustand)
- **Types**: `src/agentic_fleet/models/` (Pydantic), `src/frontend/src/types/` (TS)
- **CLI**: `src/agentic_fleet/cli/app.py` (Typer)

### Pull Request Checklist

1. Run `make check` (lint, format, type, tests)
2. Run `make validate-agents` if docs touched
3. Update relevant AGENTS.md files
4. Add tests for new workflows/agents/routes
5. Include screenshots for UI changes
6. Use Conventional Commits: `feat(api):`, `fix(workflow):`, `chore:`
