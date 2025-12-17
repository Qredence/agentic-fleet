# AgenticFleet – Copilot Instructions

AgenticFleet is a **DSPy + Microsoft agent-framework** runtime that runs a 5-phase pipeline (**analysis → routing → execution → progress → quality**) and streams structured events to the UI.

## What to read first (to orient fast)

- `src/agentic_fleet/config/workflow_config.yaml` — **source of truth** (models, agents, tools, tracing, UI event routing).
- `src/agentic_fleet/workflows/supervisor.py` — `SupervisorWorkflow.run()` / `run_stream()` (fast-path, modes, checkpoint semantics).
- `src/agentic_fleet/agents/coordinator.py` — `AgentFactory` (YAML → agents, tool + prompt resolution).
- `src/agentic_fleet/api/events/mapping.py` — maps workflow/framework events → `StreamEvent` and loads `ui_routing` from YAML.

## Non-negotiable project conventions

- **Config-driven**: don’t hardcode models/thresholds/agent rosters; change YAML and the dataclasses/helpers that load it.
- **Python deps via `uv` only** (see `Makefile`): never use `pip` directly. Frontend uses **`npm` only**.
- Code quality is enforced by **Ruff + ty** (line length 100). Use `make check` before committing.

## Developer workflows (preferred)

- Setup: `make install` (+ `make frontend-install`), then `cp .env.example .env` and set `OPENAI_API_KEY`.
- Dev: `make dev` (backend :8000 + frontend :5173) or `make backend` / `make frontend-dev`.
- Tests: `make test` (backend), `make test-frontend`, `make test-config` (validates workflow config wiring).
- Observability: `make tracing-start` / `make tracing-stop` (Jaeger UI at :16686).

## Patterns to follow when changing behavior

- **Adding/changing agents**: edit `workflow_config.yaml` under `agents:`; prompts are referenced like `instructions: prompts.planner` and resolved in `AgentFactory._resolve_instructions()`.
- **Adding tools**: implement in `src/agentic_fleet/tools/` and/or register in `ToolRegistry`; `AgentFactory` resolves tools via `ToolRegistry` first, then `agentic_fleet.tools`.
- **Streaming/UI events**: if you add a new event kind/type, update:
  - backend mapping (`src/agentic_fleet/api/events/mapping.py`) and `ui_routing:` in YAML
  - frontend types + handling (`src/frontend/src/api/types.ts`, `src/frontend/src/stores/chatStore.ts`)

## Runtime data & “where did it go?”

- Runtime artifacts live under `.var/` (gitignored): history `.var/logs/execution_history.jsonl`, workflow logs `.var/logs/workflow.log`.
- DSPy compiled artifacts may be in `.var/logs/compiled_supervisor.pkl` and/or `.var/cache/dspy/compiled_reasoner.json` (see YAML); reset with `make clear-cache`.

## HITL + resume semantics (agent-framework)

- Resume is **message XOR checkpoint_id**: to resume, call `run_stream(task=None, checkpoint_id=...)`.
- For a new run, any provided `checkpoint_id` is ignored (see `SupervisorWorkflow._run_workflow*`).
