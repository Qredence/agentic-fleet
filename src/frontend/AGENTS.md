# Repository Guidelines

## Project Structure & Module Organization

- Backend lives under `src/agentic_fleet/` with FastAPI routers in `api/`, workflow logic in `workflow/`, agents in `agents/`, and shared models in `models/`.
- Frontend sits in `src/frontend/src/` (Vite + React). UI components live in `components/`, state in `stores/`, reusable logic in `lib/`, and route-level views in `pages/`.
- Default workflows are defined in `src/agentic_fleet/workflow.yaml`; overrides can be supplied via `config/workflows.yaml` or `AF_WORKFLOW_CONFIG`.
- Tests reside in `tests/` with API, workflow, SSE, CLI, and load-testing suites; Vitest specs live alongside components in the frontend source tree.

## Build, Test, and Development Commands

- `make dev` launches FastAPI on port 8000 and `npm run dev` on 5173 for full-stack work.
- `uv run uvicorn agentic_fleet.server:app --reload --port 8000` handles backend-only loops; `make backend` wraps the same.
- `make frontend-dev` serves the SPA; produce production bundles with `make build-frontend`.
- Run backend tests with `make test` (`uv run pytest -v`) and workflow smoke checks via `make test-config`; execute Vitest with `npm run test`.

## Coding Style & Naming Conventions

- Python targets 3.12 with Ruff + Black; keep type hints explicit (`str | None`) and respect module-level `__all__` exports.
- Frontend code uses TypeScript strict mode, ESLint, and shadcn/ui primitives. Prefer 2-space indentation, PascalCase for components, and prefix custom hooks with `use`.
- Do not hardcode model IDs or tool bindings; keep workflow, agent, and tool configuration YAML-driven and return Pydantic models from tools.

## Testing Guidelines

- Co-locate Vitest specs near React modules and mirror file names with `.test.tsx` or `.test.ts`.
- Backend tests rely on Pytest; target meaningful fixtures and consider `uv run pytest --cov` when coverage metrics matter.
- After workflow or agent changes, rerun `make test-config` and the SSE bridge tests to keep schemas aligned.

## Commit & Pull Request Guidelines

- Follow Conventional Commits (`feat(frontend):`, `fix(workflow):`, `chore:`) with imperative summaries under 72 characters and optional scope.
- Reference issues in the body, describe impacts, and attach screenshots or terminal captures for UI/UX changes.
- Ensure CI-critical commands (`make check`, `npm run lint`) pass before requesting review and note any skipped validations.

## Security & Configuration Tips

- Duplicate `.env.example` to `.env`, populate `OPENAI_API_KEY` and `OPENAI_BASE_URL`, and prefer managed identity for Azure resources.
- Add tracing with `ENABLE_OTEL=true` and `OTLP_ENDPOINT`; never commit secrets—use env vars or managed stores instead.
