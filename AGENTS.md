# AGENTS.md

This repository powers the Agentic Fleet stack: a FastAPI backend, Vite/React frontend, and
documentation/test harnesses that showcase multi-agent orchestration. Treat this file as the
single source of truth for cross-cutting rules; subdirectory guides drill into details.

## Invariants (DO NOT VIOLATE)

- Always invoke Python tooling through `uv run …` (e.g. `uv run pytest`, `uv run ruff`). For JavaScript
  tasks, execute commands from `src/frontend/src/`.
- Keep workflows, docs, and tests synchronized. Any new or renamed agent/workflow must update
  `src/agentic_fleet/AGENTS.md`, `tests/AGENTS.md`, `docs/AGENTS.md`, and `src/frontend/AGENTS.md`.
- Configuration remains YAML-driven. Do not hardcode model IDs, prompts, or tool lists in Python or
  TypeScript sources—extend the YAML or `get_config()` helpers instead.
- Secrets never land in the repo. Use `.env` (ignored), environment variables, or managed stores.
- Run `make validate-agents` before publishing. Fix any blocking findings in docs or code.

## Quick Command Reference

| Command                 | Purpose                                                              |
| ----------------------- | -------------------------------------------------------------------- |
| `make install`          | Sync Python dependencies via uv (rerun after `uv.lock` updates).     |
| `make frontend-install` | Install frontend dependencies in `src/frontend/src`.                 |
| `make dev`              | Launch backend (port 8000) and frontend (port 5173) with hot reload. |
| `make check`            | Run lint (`ruff`), format (`black`), type-check (`mypy`), and tests. |
| `make test-config`      | Instantiate `WorkflowFactory` to validate YAML + agent wiring.       |
| `make validate-agents`  | Audit AGENTS docs and common documentation invariants.               |
| `uv run agentic-fleet`  | Typer CLI entry point for smoke tests and scripted flows.            |

## Repository Map

- `src/agentic_fleet/` — FastAPI backend: routers, workflow runtime, agent registry, tools.
- `src/frontend/src/` — Vite + React app: components, stores, hooks, and utility modules.
- `tests/` — Backend Pytest suites plus load-testing utilities under `tests/load_testing/`.
- `docs/` — Architecture notes, API references, CLI guides, and supporting media.
- `tools/`, `notebooks/`, `assets/`, `config/pytest.ini`, `var/` — Scripts, experiments, shared
  assets, Pytest config, and runtime data.
- `scripts/`, `specs/`, `PLANS.md` — Auxiliary automation, design documents, and planning trails.

## Development Workflow

- **Setup**: `make install` then `make frontend-install`. Use `make dev-setup` for the bundled flow.
- **Daily loop**: Run `make dev` for full-stack work or `make backend` / `make frontend-dev` to focus
  on one side. The backend reads configuration from `.env` and the packaged `src/agentic_fleet/workflow.yaml` (or a path supplied via `AF_WORKFLOW_CONFIG`).
- **CLI**: `uv run agentic-fleet` (aliased to `uv run fleet`) exposes scripted interactions and quick
  workflow checks. Add new commands under `src/agentic_fleet/cli/`.
- **Config overrides**: Point `AF_WORKFLOW_CONFIG` to an absolute YAML file if you need an alternate workflow set. Otherwise edit `src/agentic_fleet/workflow.yaml`. Avoid committing environment-specific overrides.

## Coding Standards

- **Python**: Target 3.12, explicit typing, 4-space indentation, 100-character lines. Keep imports
  sorted, prefer `pathlib`, and guard module exports with `__all__`. Use the logging helpers in
  `src/agentic_fleet/utils/logging.py`.
- **Frontend**: TypeScript strict mode, two-space indentation, PascalCase components, camelCase
  hooks/functions. Organize feature assets together and prefer barrel exports when it improves
  readability.
- **Formatting**: `uv run ruff check --fix .` and `uv run black .` for backend; Prettier and ESLint
  (via `npm run lint`) for the frontend. Do not mix formatting-only changes with logic in commits.

## Testing Checklist

- `make test` (alias for `uv run pytest -v`) covers the backend. Use `uv run pytest -k <pattern>` for
  focused runs and `uv run pytest --cov=src/agentic_fleet --cov-report=term-missing` when tracking
  coverage.
- Start both services (`make dev`) before `make test-e2e` to execute Playwright flows.
- `npm run test` from `src/frontend/src` drives Vitest suites. Snapshot updates require reviewer
  acknowledgement.
- Load testing lives under `tests/load_testing/`; run `make load-test-smoke|load|stress` with the API
  running locally.
- Refresh documentation invariants with `make validate-agents` whenever AGENTS content changes.

## Documentation Chain

- `docs/AGENTS.md` governs authoring standards for Markdown-style documentation.
- `src/agentic_fleet/AGENTS.md` documents backend architecture, workflow wiring, and agent personas.
- `src/frontend/AGENTS.md` captures SPA structure, state management, and SSE integration points.
- `tests/AGENTS.md` maps coverage areas and how to execute the suites.
- Update cross-references when paths, commands, or workflows move. Regenerate diagrams or assets in
  `assets/` when documentation calls them out.

## Release & Pull Request Guidelines

- Use Conventional Commits (`feat(frontend): …`, `fix(api): …`, `chore:`) with succinct imperative
  summaries (~72 characters) and optional scopes.
- Keep changelog notes in PR descriptions: affected workflow IDs, new endpoints, or UI changes.
- Attach screenshots or terminal transcripts for UX-visible updates. Mention skipped checks or
  follow-up tasks explicitly.
- Run `make check` before review. Follow up with `make validate-agents` if docs were touched and note
  any intentional deviations.

## Agent Configuration Tips

- Define personas inside `src/agentic_fleet/agents/` (`get_config()` functions returning dictionaries)
  and register them in `src/agentic_fleet/workflows.yaml` (or an override provided via `AF_WORKFLOW_CONFIG`).
- Ensure new prompts live under `src/agentic_fleet/prompts/`. Modules should expose
  `get_instructions()` for reuse.
- Maintain alignment between YAML workflow IDs, entity metadata, and tests. Update `tests/AGENTS.md`
  and relevant suites (`test_workflow_factory.py`, `test_event_bridge.py`) when orchestrations change.
- Rerun `make validate-agents` after editing this document or any AGENTS sibling to keep the doc chain
  synchronized with code.
