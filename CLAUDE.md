# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgenticFleet is a multi-agent orchestration system combining DSPy + Microsoft Agent Framework. Tasks flow through a 5-phase pipeline: **Analysis → Routing → Execution → Progress → Quality**. Supports delegated, sequential, parallel, handoff, and discussion execution modes.

## Development Commands

| Task                 | Command                                            |
| -------------------- | -------------------------------------------------- |
| Install dependencies | `make install` (uses uv)                           |
| Full-stack dev       | `make dev` (backend :8000, frontend :5173)         |
| Backend only         | `make backend`                                     |
| Frontend only        | `make frontend-dev`                                |
| Run tests            | `make test`                                        |
| Run single test      | `uv run pytest tests/path/test_file.py::test_name` |
| Lint + type check    | `make check`                                       |
| Format code          | `make format`                                      |
| Frontend lint        | `make frontend-lint`                               |
| Clear DSPy cache     | `make clear-cache`                                 |
| CLI task             | `agentic-fleet run -m "your task" --verbose`       |

**Package managers**: `uv` for Python (never pip directly), `npm` for frontend (not bun).

## Architecture

```
src/agentic_fleet/
├── agents/           # Agent definitions, AgentFactory (coordinator.py)
├── workflows/        # Orchestration: supervisor.py (entry), executors.py (phases)
├── dspy_modules/     # DSPy signatures (signatures.py), reasoner (reasoner.py)
├── tools/            # Tool adapters (Tavily, browser, MCP, code interpreter)
├── app/              # FastAPI backend + SSE streaming
├── config/           # workflow_config.yaml - source of truth for all settings
├── core/             # Middleware (ChatMiddleware, BridgeMiddleware)
└── utils/            # Shared helpers, ToolRegistry, HistoryManager
src/frontend/         # React/Vite UI (state in hooks/useChat.ts)
```

**Config-Driven**: Models, agents, thresholds, and tools are declared in `src/agentic_fleet/config/workflow_config.yaml`. Reference YAML values—don't hardcode.

## Key Conventions

### Python

- Python 3.12+ with modern syntax (`type | None`, not `Optional[type]`)
- Strict typing with `ty` checker; avoid `Any`
- Absolute imports: `from agentic_fleet.utils import ...`
- Line length: 100 chars (Ruff enforced)
- Run quality checks before commits: `make check`

### DSPy Integration

- **Compilation is offline only**—never compile at runtime
- Signatures: `src/agentic_fleet/dspy_modules/signatures.py`
- Cache: `.var/logs/compiled_supervisor.pkl`
- Clear cache after modifying DSPy modules: `make clear-cache`
- Examples: `src/agentic_fleet/data/supervisor_examples.json`

### Frontend (React/TypeScript)

- State: Chat state in `hooks/useChat.ts`
- API calls: Always through `lib/api/` (never direct fetch)
- Components: Shared atoms in `components/ui/` (shadcn/ui)
- Config: `VITE_API_URL` in `.env` (defaults to `http://localhost:8000`)

## Common Tasks

### Adding an Agent

1. Add config to `workflow_config.yaml` under `agents:`
2. Add prompts to `src/agentic_fleet/agents/prompts.py` (referenced as `prompts.<name>`)
3. Tools auto-resolve via `ToolRegistry`; list tool names in YAML

### Adding a Tool

1. Create adapter in `src/agentic_fleet/tools/` (extend base patterns)
2. Add to agent's `tools:` list in workflow_config.yaml (auto-discovered)

### Modifying Workflow Phases

- Executors: `workflows/executors.py` (AnalysisExecutor, RoutingExecutor, etc.)
- Strategies: `workflows/strategies.py` (delegated/sequential/parallel)
- Streaming: `workflows/execution/streaming_events.py`

## Environment Variables

**Required**: `OPENAI_API_KEY`

**Optional**: `TAVILY_API_KEY` (web search), `DSPY_COMPILE=false` (skip recompilation), `ENABLE_OTEL` + `OTLP_ENDPOINT` (tracing), `LOG_JSON=0` (human-readable logs)

Copy `.env.example` → `.env` for local development.

## Runtime Data

All caches, logs, and history live under `.var/` (gitignored). Key locations:

- DSPy compiled cache: `.var/logs/compiled_supervisor.pkl`
- Execution history: `.var/logs/execution_history.jsonl`
- Conversations: `.var/data/conversations.json`
- GEPA optimization logs: `.var/logs/gepa/`

## Debugging Tips

- **Routing issues**: Check `.var/logs/execution_history.jsonl` for decisions
- **Slow workflows**: Reduce `gepa_max_metric_calls` in workflow_config.yaml, or use `--fast` flag
- **DSPy fallback**: If no compiled cache, system uses zero-shot (set `require_compiled: true` in production)
- **Frontend not connecting**: Verify `VITE_API_URL` matches backend port

## Files to Read First

1. `src/agentic_fleet/config/workflow_config.yaml` — All runtime settings
2. `src/agentic_fleet/workflows/supervisor.py` — Main orchestration entry
3. `src/agentic_fleet/agents/coordinator.py` — AgentFactory (creates agents from YAML)
4. `AGENTS.md` (root) — Toolchain defaults and working agreements

- Use "uv" for the project, always make sure that @CLAUDE.md is up to date
- When making changes in the project, always remember to add it to @CHANGELOG.md
- Remember the goal/purpose of the project and the synergy between agent-framework and dspy
- make sure to get the official documentation of DSPy and Agent-Framework when needed
