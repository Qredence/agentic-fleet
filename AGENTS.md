# AGENTS.md

## Project Overview

AgenticFleet is a uv-first, YAML-driven multi-agent orchestration platform that pairs a FastAPI backend with a Vite/React frontend. The system implements Microsoft's Magentic Fleet pattern, letting a manager agent spawn and supervise specialist agents (researcher, coder, analyst, planner, reviewer, etc.) while enforcing human-in-the-loop approval and structured tool contracts. Everything in the runtime is configured declaratively via `config/workflows.yaml` and `src/agentic_fleet/agents/*/config.yaml`, so coding agents must respect the configuration-first design when making changes.

## Invariants (DO NOT VIOLATE)

- **Always** invoke Python tooling through `uv run …`. Direct interpreter or test-runner invocations outside the uv sandbox will fail CI and violate repo policy.
- Agent models, prompts, and tool wiring **must** remain YAML-driven. Never hardcode `model_id` arguments or prompts inside Python modules; adjust the corresponding YAML and rerun `make test-config` instead.
- All tools return Pydantic models from `src/agentic_fleet/core/code_types.py`. Preserve those return types and keep new tool outputs compliant.
- Keep type hints strict. Every new Python function needs explicit annotations using Python 3.12 syntax (e.g. `str | None`).
- Protect credentials: populate `.env` locally via `cp .env.example .env`, never commit secrets, and prefer managed identity when wiring Azure resources.
- After touching any AGENTS documentation, execute `uv run python tools/scripts/validate_agents_docs.py` and resolve errors before merging.

## Environment Setup

1. Install prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 20+ (ships with npm), and an OpenAI key.
2. Bootstrap Python dependencies and dev extras with `make install` (wraps `uv sync`).
3. Install frontend packages once via `make frontend-install` (runs `npm install` inside `src/frontend`).
4. Copy `cp .env.example .env`, then add `OPENAI_API_KEY` (and Azure credentials if you plan to exercise cloud integrations such as Cosmos DB, Mem0, or Azure AI Search).
5. Optional: run `make dev-setup` to chain install, frontend install, and pre-commit hook configuration.

## Development Workflow

- Full stack (backend + frontend hot reload): `make dev` or `uv run agentic-fleet`.
- Backend API only: `uv run uvicorn agentic_fleet.server:app --reload --port 8000` (port configurable through `--port`).
- CLI / REPL workflow: `uv run fleet` launches the Typer-based console.
- Frontend alone: `make frontend-dev` or `cd src/frontend && npm run dev` (expects backend at `http://localhost:8000`).
- Update dependencies when lockfiles change using `make sync` for Python or rerunning `npm install` for the frontend.
- Any change to YAML configs demands `make test-config` to ensure `WorkflowFactory` can hydrate every workflow definition.

## Testing Instructions

- Run the backend suite with `make test` (wraps `uv run pytest -v`). Focused runs look like `uv run pytest tests/test_api_conversations.py -k happy_path`.
- Validate configuration and agent loading paths with `make test-config` (fast guardrail required after editing YAML or AGENTS docs).
- Execute frontend tests from `src/frontend` using `npm run test` or `npm run test -- --watch` for interactive Vitest sessions.
- Playwright end-to-end tests live in `tests/test_backend_e2e.py` and the `tests/e2e` folder; run `make test-e2e` only after the dev stack is up.
- Keep coverage optional but available via `uv run pytest --cov` if you need metrics for backend changes.

## Quality Gates & Tooling

- Linting: `make lint` (Ruff) and `make format` (Ruff fix + Black) enforce formatting. Always re-run after touching Python modules.
- Types: `make type-check` (strict mypy) must be green before merging backend work.
- AGENTS doc hygiene: `uv run python tools/scripts/validate_agents_docs.py --format text` surfaces missing docs, table spacing issues, or policy violations.
- Git hooks: install once with `uv run pre-commit install` (or `make pre-commit-install`).

## Build, Packaging, and Deployment

- Backend builds run through Hatch/uv packaging: `uv build` (or `uv run python -m build`) emits wheels/sdists when required.
- Frontend production assets come from `cd src/frontend && npm run build`, producing output in `dist/` for the Vite app.
- Deployments rely on environment variables: configure `AF_WORKFLOW_CONFIG` to point at custom workflow YAML, and set Cosmos / Redis / Mem0 endpoints when enabling optional persistence layers.

## Observability & Integrations

- Enable tracing with `ENABLE_OTEL=true` plus a live collector at `OTLP_ENDPOINT`. Local development uses `tools/observability/run-otel-collector.sh`.
- To persist conversations in Azure Cosmos DB, set the `AGENTICFLEET_USE_COSMOS` flag alongside endpoint/key/database container variables provided in `.env.example`. Follow the Cosmos partitioning guidance when provisioning containers.
- Long-term memory comes from Mem0; provide `MEM0_API_KEY` and configure `MEM0_HISTORY_DB_PATH` before enabling related providers.

## Quick Command Reference

- `make install` — Install Python dependencies via uv.
- `make frontend-install` — Install frontend dependencies with npm.
- `make dev` — Launch backend (port 8000) and frontend (port 5173) together.
- `uv run uvicorn agentic_fleet.server:app --reload --port 8000` — Backend API only.
- `cd src/frontend && npm run dev` — Frontend dev server only.
- `make test` — Run backend test suite.
- `make test-config` — Validate workflow/agent configuration.
- `cd src/frontend && npm run test` — Execute frontend Vitest suite.
- `make check` — Run Ruff lint + mypy type checks.
- `uv run python tools/scripts/validate_agents_docs.py` — Audit AGENTS documentation invariants.

## Troubleshooting & Support

- If `uv run` commands complain about missing interpreter extras, rerun `make install` to refresh the lockfile environment.
- HTTP 401/403 errors usually mean the OpenAI key (or Azure credentials) are absent; confirm `.env` is loaded before launching servers.
- Frontend SSE hangs often trace back to the backend not running; check `http://localhost:8000/v1/system/health` via curl or browser.
- Use `var/checkpoints/` to resume workflows: `uv run fleet --resume <checkpoint-id>`.
- Persistent validation failures in AGENTS docs? Run `uv run python tools/scripts/validate_agents_docs.py --format json` for precise file/line diagnostics.

## Related AGENTS Documentation

- `docs/AGENTS.md` — authoring and formatting guidelines for Markdown content.
- `src/agentic_fleet/AGENTS.md` — backend module map, API entry points, and coding standards.
- `src/frontend/AGENTS.md` — React/Vite workflow, testing, and UI conventions.
