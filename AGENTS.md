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

## Agents & Orchestration

- Stack: DSPy + Microsoft `agent-framework` (magentic-fleet pattern). Agents live under `src/agentic_fleet/agents/`; orchestration in `src/agentic_fleet/workflows/`; DSPy reasoning in `src/agentic_fleet/dspy_modules/`.
- **5-Phase Pipeline** (v0.6.6): `analysis → routing → execution → progress → quality`. Judge phase removed for ~66% latency reduction.
- **Offline Layer**: DSPy compilation is strictly offline (via `scripts/optimize.py`). Runtime uses cached modules (`.var/logs/compiled_supervisor.pkl`) and never compiles on the fly.
- **Dynamic Prompts**: Agent instructions (e.g., Planner) are generated dynamically via DSPy signatures (`PlannerInstructionSignature`) and optimized offline.
- **Middleware**: `ChatMiddleware` handles cross-cutting concerns. `BridgeMiddleware` captures runtime history for offline learning.
- Routing/quality loops configured via `config/workflow_config.yaml`; history & tracing in `.var/logs/execution_history.jsonl`.
- **Group Chat**: Multi-agent discussions are supported via `DSPyGroupChatManager` and `GroupChatBuilder`. Workflows can participate as agents using the `workflow.as_agent()` pattern.
- **Latency Tips**: Clear DSPy cache after changes (`make clear-cache`), use `gpt-5-mini` for routing, disable judge if not needed.
- When adding or modifying agents/workflows, keep prompts/factories in sync and update config schema validation.
- For multi-agent expansion with OpenAI Agents SDK, treat Codex CLI as an MCP server and mirror roles from `.github/agents/agent-framework-spec.md`; document new roles/prompts here and in `docs/` as needed.

## Conventions & Notes

- Keep code typed; follow Ruff/ty defaults (line length 100, py312 syntax, docstrings for public APIs).
- Avoid committing artifacts from `.var/` (logs, caches, compiled DSPy outputs).
- Prefer `make` targets over raw commands; if adding new workflows/tests, add a Make target and update this file.
- If you change how to start, test, or observe the system, append the updated commands here and, for larger shifts, create an ExecPlan entry in `docs/plans/current.md`.
