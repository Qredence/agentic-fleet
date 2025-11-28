# AgenticFleet Copilot Instructions

## Project Overview

AgenticFleet is a hybrid **DSPy + Microsoft Agent Framework** runtime for multi-agent orchestration.

- **Core Logic**: `src/agentic_fleet/` (Backend), `src/frontend/` (React/Vite UI).
- **Architecture**: 5-Phase Pipeline: Analysis → Routing → Execution → Progress → Quality.
- **Key Config**: `config/workflow_config.yaml` controls models, agents, thresholds, and tracing. **Never hardcode these in Python.**

## Critical Workflows

- **Package Management**: Uses `uv`. Never use `pip` directly.
  - Install: `make install` (syncs all dependencies).
  - Add dependency: `uv add <package>` (then run `make install`).
- **Development**:
  - Full Stack: `make dev` (Backend :8000, Frontend :5173).
  - Backend only: `make backend`.
  - Frontend only: `make frontend-dev`.
- **Quality Gates**:
  - Run all checks: `make check` (Linting + Formatting + Type Checking).
  - Tests: `make test` (Backend), `make test-frontend` (Frontend).
  - **Always run `make check` before committing.**

## Codebase Conventions

- **Python (Backend)**:
  - **Version**: Python 3.12+. Use modern syntax (e.g., `type | None` instead of `Optional[type]`).
  - **Typing**: Strict typing required. Use `ty` for checking. Avoid `Any`.
  - **Imports**: Use absolute imports from `agentic_fleet` (e.g., `from agentic_fleet.utils import ...`).
  - **DSPy**:
    - Signatures live in `src/agentic_fleet/dspy_modules/signatures.py`.
    - Compilation is **offline**. Do not compile at runtime.
    - Cache: `logs/compiled_supervisor.pkl`. Clear with `uv run python -m agentic_fleet.scripts.manage_cache --clear`.
- **TypeScript/React (Frontend)**:
  - **State**: `src/frontend/src/stores/chatStore.ts` (Zustand) is the single source of truth.
  - **API**: Use `src/frontend/src/lib/api/` for backend calls.
  - **Components**: `src/frontend/src/components/ui/` for shared atoms (shadcn/ui).

## Key Files & Directories

- `config/workflow_config.yaml`: **Read this first** to understand active agents and models.
- `src/agentic_fleet/workflows/supervisor.py`: Main orchestration logic.
- `src/agentic_fleet/dspy_modules/reasoner.py`: DSPy logic for analysis and routing.
- `src/agentic_fleet/agents/`: Agent definitions. Register new agents in `config/workflow_config.yaml`.
- `logs/execution_history.jsonl`: Execution logs for debugging routing/quality issues.

## Common Tasks

- **Adding an Agent**:
  1. Create module in `src/agentic_fleet/agents/`.
  2. Add prompts to `src/agentic_fleet/agents/prompts.py`.
  3. Register in `config/workflow_config.yaml` under `agents:`.
  4. Update `docs/developers/internals/AGENTS.md`.
- **Adding a Tool**:
  1. Implement adapter in `src/agentic_fleet/tools/`.
  2. Register in `src/agentic_fleet/utils/tool_registry.py`.
  3. Add to `config/workflow_config.yaml`.

## Debugging

- **Backend**: Use `agentic-fleet run -m "task" --verbose` for CLI debugging.
- **Frontend**: Check `VITE_API_URL` in `.env`.
- **DSPy**: If routing is poor, inspect `logs/execution_history.jsonl` and consider updating examples in `src/agentic_fleet/data/supervisor_examples.json`.
