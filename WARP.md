# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Stack overview

- Backend: FastAPI (Python 3.12) under `src/agentic_fleet/`
- Frontend: Vite/React/TypeScript under `src/frontend/`
- Orchestration: YAML‑driven multi‑agent workflows (no hardcoded model IDs/prompts/tools)
- Python tooling is uv‑managed; always run Python commands via `uv run ...`

## Commands you’ll use often

Setup

```bash
make install            # sync Python deps via uv
make frontend-install   # install frontend deps (runs in src/frontend)
make dev-setup          # install + frontend + pre-commit
```

Run (dev)

```bash
make dev           # backend (8000) + frontend (5173)
make backend       # uvicorn backend only
make frontend-dev  # vite frontend only
make build-frontend  # build SPA into src/agentic_fleet/ui
make run           # uv run python -m agenticfleet (CLI entry)
uv run agentic-fleet --help  # Typer CLI (alias: uv run fleet)
```

Tests

```bash
make test                      # backend tests (pytest)
uv run pytest -k <expr>        # run a subset (e.g., -k streaming)
uv run pytest tests/test_api_responses_streaming.py::TestStream::test_happy_path  # single test
uv run pytest --cov=src/agentic_fleet --cov-report=term-missing  # coverage
make test-config               # validate YAML + wiring via WorkflowFactory
make test-frontend             # Vitest (runs in src/frontend)
make test-e2e                  # Playwright (requires make dev)
```

Quality gates

```bash
make lint            # ruff
make format          # ruff --fix + black
make type-check      # mypy
make check           # lint + type-check (and prints summary)
make validate-agents # docs invariants across AGENTS.md files
```

Load testing

```bash
make load-test-setup
make load-test-smoke | load-test-load | load-test-stress | load-test-dashboard
# Or cd tests/load_testing and use its Makefile for advanced scenarios
```

Config & environment

- Required: `OPENAI_API_KEY` in `.env` (see `.env.example`)
- Override workflows: `AF_WORKFLOW_CONFIG=/abs/path/to/custom.yaml`
- Default dev ports: backend 8000, frontend 5173

## High‑level architecture (big picture)

Configuration and workflow resolution

- Resolution order: `AF_WORKFLOW_CONFIG` (absolute path) → packaged default `src/agentic_fleet/workflows.yaml`
- Repo ships a convenience override in `config/workflows.yaml` (keep in sync with the packaged default)

Backend orchestration pipeline

- YAML selects a workflow ID → `utils.factory.WorkflowFactory` constructs a `MagenticFleetWorkflow`
- Manager + specialists (planner, executor, coder, verifier, generator) are instantiated from `agents/*.py` via `get_config()`; tools resolve through `tools/registry.py`
- Events produced by the workflow pass through `workflow/events.WorkflowEventBridge`
- `api/responses/service.ResponseAggregator` adapts events into OpenAI Responses‑compatible payloads for REST/SSE
- FastAPI app is created in `api/app.py` and exposed via `server.py` (`agentic_fleet.server:app`)

API surface (selected)

- `/v1/responses` (with optional SSE), `/v1/entities` (advertises workflow IDs), `/v1/workflows/*`, `/v1/system/*`, compatibility shims under `/v1/chat/completions`

Frontend data flow

- `lib/api/chat.ts` opens SSE to `/v1/responses`; `lib/parsers/*` translate payloads
- `stores/chatStore.ts` (Zustand) is the single source of truth for messages/telemetry
- UI renders chat and orchestration progress from store state
- Production build via `make build-frontend` outputs static assets to `src/agentic_fleet/ui`, served by the backend

Where to extend the system

- New/changed agents: add `get_config()` under `src/agentic_fleet/agents/<role>.py`, register in `workflows.yaml`, update `agents/__init__.py`, and cover in `tests/test_workflow_factory.py`
- New tools: register in `tools/registry.py`; prefer Pydantic models for IO; mock in tests
- Event/schema changes: update `workflow/events.py` and `api/responses/service.py`, then align frontend parsers and store; test with `tests/test_api_responses_streaming.py`
- API routes: add under `src/agentic_fleet/api/<domain>/routes.py` and mount in `api/app.py`

Conventions (from repo AI‑agent guidelines)

- Always prefix Python CLIs with `uv run` (pytest/ruff/black/mypy/uvicorn/CLI)
- Keep config declarative: model IDs, prompts, and tool lists live in YAML or `prompts/*.py`, not in Python/TS source
- Run frontend tooling from `src/frontend` (`npm run {dev,build,lint,test}`); use the Make targets from repo root for convenience
- Keep AGENTS docs synchronized; run `make validate-agents` when changing agents/workflows/docs
- Tests should mock external services; avoid hitting real OpenAI/Mem0 in CI

Read more

- Root overview and quick start: `README.md`
- Backend architecture & workflows: `src/agentic_fleet/AGENTS.md`
- Frontend structure & SSE integration: `src/frontend/AGENTS.md`
- Tests organization & examples: `tests/AGENTS.md`
- Documentation authoring standards: `docs/AGENTS.md`
