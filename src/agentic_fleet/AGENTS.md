# AGENTS.md

## Overview

This directory houses the FastAPI backend, Typer CLI, workflow factories, and integration shims that implement the Magentic Fleet runtime. All API routers, approval flows, and configuration loading live here. Code in this tree **must** remain YAML-driven—agent metadata, tool wiring, and workflow limits belong in configuration files, not hardcoded constants.

## Directory Map

- `api/` — FastAPI routers (`/v1/chat`, `/v1/conversations`, approvals, workflow discovery`).
- `api/workflow_factory.py` — Resolves workflow YAML from `AF_WORKFLOW_CONFIG`, `config/workflows.yaml`, or packaged defaults.
- `workflow.yaml` — Packaged fallback workflows bundled with the package distribution.
- `server.py` — Uvicorn entry point (`agentic_fleet.server:app`).
- `cli/` — Typer CLI stub exposed via `uv run fleet`.
- `core/context/` — Context providers (Mem0, Redis, etc.).
- `integrations/` — MCP and Mem0 integration notes.

## Environment & Setup

- Python version: 3.12+. Manage dependencies with uv; never install via pip directly.
- Configure `.env` in the repo root for secrets (`OPENAI_API_KEY`, optional Cosmos/Mem0 variables, OTEL settings). Backend modules read them through `agentic_fleet.config.settings`.
- When developing locally, export `AF_WORKFLOW_CONFIG` if you need to point at a custom workflows file outside the repo.

## Running the Backend

- Dev server with auto-reload: `uv run uvicorn agentic_fleet.server:app --reload --port 8000`.
- CLI access: `uv run fleet` (aliases: `uv run agentic-fleet`, `uv run workflow`). Extend commands by adding Typer subcommands in `cli/app.py`.
- Full stack (backend + frontend): run from repo root with `make dev`.
- Health check endpoint: `GET /v1/system/health` (used by Playwright tests and frontend readiness probes).

## Testing & Validation

- API and workflow tests live in `tests/`. Execute the suite with `make test` or target specific files via `uv run pytest tests/test_api_health.py`.
- Configuration guardrail: `make test-config` ensures `WorkflowFactory` can deserialize every workflow and that agent directories resolve.
- For regression scenarios focused on SSE or orchestration, use `uv run pytest tests/test_magentic_backend_integration.py`.
- Keep mocks for external services (OpenAI, Mem0, Redis) intact; tests assume no real network traffic.

## Coding Standards

- New modules require explicit `__all__` exports where appropriate and strict type hints. Use `TypeAlias` or TypedDict where structured data crosses module boundaries.
- Tools returning structured data must subclass/instantiate models in `src/agentic_fleet/core/code_types.py` to maintain parsing guarantees for downstream agents.
- Mind approval gates. Sensitive operations should call helpers from `src/agentic_fleet/core/approval.py` rather than bypassing human-in-the-loop logic.
- Respect the separation between packaged defaults (`agentic_fleet/workflow.yaml`) and repo-level overrides (`config/workflows.yaml`). Do not edit the packaged file when customizing workflows during development; modify the repo override instead.
- Treat logging and observability consistently: rely on the eventing/callback framework instead of printing directly to stdout.

## Quick Reference

- `uv run uvicorn agentic_fleet.server:app --reload --port 8000` — Start dev API.
- `uv run fleet` — Launch the CLI.
- `make dev` — Run backend + frontend together.
- `make test` — Execute backend tests.
- `make test-config` — Validate YAML-driven workflows.
- `make type-check` — Run mypy.
- `make lint` / `make format` — Ruff lint and format.
- `uv run python tools/scripts/validate_agents_docs.py` — Audit AGENTS docs.

## Troubleshooting

- `WorkflowFactory` can't find configs? Confirm `AF_WORKFLOW_CONFIG` points to an existing file or that `config/workflows.yaml` remains in sync with packaged defaults.
- Runtime errors loading agents typically stem from missing directories under `src/agentic_fleet/agents/`; ensure every workflow entry references an actual agent module with `__init__.py`.
- 401 errors from hosted tools generally indicate missing approval scaffolding. Double-check approval routes in `api/approvals/` and the `ApprovalDecision` usage.
- For Cosmos/Mem0 integrations, be mindful of async clients—use lifespan events or dependency overrides to share connection pools.
