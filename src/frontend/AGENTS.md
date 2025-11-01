# Repository Guidelines

## Project Structure & Module Organization

- `config/workflows.yaml` and `src/agentic_fleet/agents/*/config.yaml` define all agent behavior; adjust YAML rather than hardcoding logic.
- Backend code lives in `src/agentic_fleet/`, with tests in `tests/` and utilities under `tools/`.
- The React/Vite frontend resides in `src/frontend/src`, static assets in `src/frontend/public`, and build output in `src/frontend/dist`.
- Shared documentation sits in `docs/` and `src/frontend/AGENTS.md`; keep this file updated alongside related guides.

## Build, Test, and Development Commands

- `make install` — sync Python dependencies via `uv`; rerun after lockfile updates.
- `make dev` — launch FastAPI (port 8000) and Vite (port 5173) with hot reload.
- `uv run uvicorn agentic_fleet.server:app --reload --port 8000` — backend-only loop for API work.
- `make frontend-install` then `npm run dev` — install and run the frontend in isolation.
- `make test`, `make test-config`, and `npm run test` — run backend pytest, config hydration guardrails, and Vitest respectively.

## Coding Style & Naming Conventions

- Target Python 3.12 with explicit type hints (`str | None` style) and prefer data classes or Pydantic models declared in `core/code_types.py`.
- All Python tooling, linters, and scripts run through `uv run …`; never invoke `python` directly.
- Use Ruff and Black (`make format`) plus Mypy (`make type-check`); keep YAML declarative and avoid embedding prompts or model IDs in code.
- Follow React conventions: PascalCase components in `src/frontend/src/components`, camelCase hooks/utilities, and 2-space indentation.

## Testing Guidelines

- Backend uses `pytest`; name modules `test_*.py` and co-locate fixtures in `tests/conftest.py`.
- Frontend relies on Vitest and Testing Library; name specs `*.test.ts(x)` beside the component.
- Run `make test-config` after any YAML or AGENTS.md change to ensure workflows hydrate correctly.
- Optional coverage is available with `uv run pytest --cov`; keep failures reproducible by recording seed or env flags when relevant.

## Commit & Pull Request Guidelines

- Write concise imperative subjects (e.g., `Add planner retry budget`) and reference issues or PRs with `(#123)` when applicable.
- Bundle related changes only; ensure lint, tests, and `make test-config` pass before requesting review.
- PRs should describe intent, call out config or schema updates, and include screenshots or CLI output for UI-affecting work.
- After editing AGENTS documentation, run `uv run python tools/scripts/validate_agents_docs.py` and attach the passing snippet in the PR.

## Security & Configuration Tips

- Copy `.env.example` to `.env`, provide `OPENAI_API_KEY`, and rely on managed identities for Azure secrets; never commit credentials.
- Set `AF_WORKFLOW_CONFIG` when using custom workflow files and validate with `make test-config` before deploying.
- Enable tracing by exporting `ENABLE_OTEL=true` and pointing `OTLP_ENDPOINT` at a running collector (`tools/observability/run-otel-collector.sh`).
