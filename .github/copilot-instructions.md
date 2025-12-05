# AgenticFleet Copilot Instructions

## Project Overview

AgenticFleet is a hybrid **DSPy + Microsoft Agent Framework** runtime for multi-agent orchestration. The system routes tasks through a 5-phase pipeline (Analysis → Routing → Execution → Progress → Quality) and supports delegated, sequential, parallel, handoff, and discussion execution modes.

## Architecture Quick Reference

```
src/agentic_fleet/
├── agents/           # Agent definitions + AgentFactory (coordinator.py)
├── workflows/        # Orchestration: supervisor.py (entry), executors.py (phases)
├── dspy_modules/     # DSPy signatures (signatures.py) + reasoner (reasoner.py)
├── tools/            # Tool adapters (Tavily, browser, MCP bridges, code interpreter)
├── app/              # FastAPI backend + SSE streaming
├── config/           # workflow_config.yaml - THE source of truth for all settings
└── utils/            # Shared helpers, ToolRegistry, HistoryManager, caching
src/frontend/         # React/Vite UI (state managed in hooks/useChat.ts)
```

**Config-Driven Architecture**: All models, agents, thresholds, and tools are declared in `src/agentic_fleet/config/workflow_config.yaml`. Never hardcode these values in Python—reference the YAML.

## Development Commands (Use `make` Targets)

| Task                 | Command                                         |
| -------------------- | ----------------------------------------------- |
| Install dependencies | `make install` (uv sync)                        |
| Full stack dev       | `make dev` (backend :8000, frontend :5173)      |
| Backend only         | `make backend`                                  |
| Frontend only        | `make frontend-dev`                             |
| Run tests            | `make test` (backend), `make test-frontend`     |
| Lint + type check    | `make check` ← **Always run before committing** |
| Clear DSPy cache     | `make clear-cache`                              |
| CLI task             | `agentic-fleet run -m "your task" --verbose`    |

**Package manager**: `uv` only. Never use `pip` directly. Add dependencies with `uv add <package>`.

## Key Conventions

### Python (Backend)

- **Python 3.12+** with modern syntax (`type | None`, not `Optional[type]`)
- **Strict typing**: Use `ty` checker; avoid `Any`
- **Absolute imports**: `from agentic_fleet.utils import ...`
- **Line length**: 100 chars (Ruff enforced)

### DSPy Integration

- **Compilation is offline only**—never compile at runtime
- Signatures: `src/agentic_fleet/dspy_modules/signatures.py`
- Cache: `.var/logs/compiled_supervisor.pkl`
- Clear cache after modifying DSPy modules: `make clear-cache`
- Examples: `src/agentic_fleet/data/supervisor_examples.json`

### Frontend (React/TypeScript)

- **State**: Chat state managed in `hooks/useChat.ts` (React hooks). Zustand installed for future global state needs.
- **API calls**: Always through `lib/api/` (never direct fetch)
- **Components**: Shared atoms in `components/ui/` (shadcn/ui)
- **Config**: `VITE_API_URL` in `.env` (defaults to `http://localhost:8000`)

## Common Tasks

### Adding an Agent

1. Add config to `src/agentic_fleet/config/workflow_config.yaml` under `agents:`
2. Add prompts to `src/agentic_fleet/agents/prompts.py` (referenced as `prompts.<name>`)
3. Tools auto-resolve via `ToolRegistry`; just list tool names in YAML

### Adding a Tool

1. Create adapter in `src/agentic_fleet/tools/` (extend base patterns)
2. Tool is auto-discovered; add to agent's `tools:` list in workflow_config.yaml

### Modifying Workflow Phases

- Executors: `workflows/executors.py` (AnalysisExecutor, RoutingExecutor, etc.)
- Strategies: `workflows/strategies.py` (delegated/sequential/parallel)
- Streaming: `workflows/execution/streaming_events.py`

## Environment Variables

**Required**: `OPENAI_API_KEY`
**Optional**: `TAVILY_API_KEY` (web search), `DSPY_COMPILE=false` (skip recompilation), `ENABLE_OTEL` + `OTLP_ENDPOINT` (tracing)

Copy `.env.example` → `.env` for local development.

## Debugging Tips

- **Routing issues**: Check `.var/logs/execution_history.jsonl` for decisions
- **Slow workflows**: Reduce `gepa_max_metric_calls` in workflow_config.yaml, or use `--fast` flag
- **DSPy fallback**: If no compiled cache exists, system uses zero-shot (set `require_compiled: true` in production)
- **Frontend not connecting**: Verify `VITE_API_URL` matches backend port

## Files to Read First

1. `src/agentic_fleet/config/workflow_config.yaml` — All runtime settings
2. `src/agentic_fleet/workflows/supervisor.py` — Main orchestration entry
3. `src/agentic_fleet/agents/coordinator.py` — AgentFactory (creates agents from YAML)
4. `AGENTS.md` (root) — Toolchain defaults and working agreements
