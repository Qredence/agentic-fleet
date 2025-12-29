---
label: project
description: Project architecture, tech stack, and key conventions. Always in-context for coding tasks.
limit: 10000
scope: core
updated: 2024-12-29
---

# Project Context: AgenticFleet

## Architecture Overview

The codebase follows a **layered API → Services → Workflows → DSPy → Agents** architecture:

```
src/agentic_fleet/
├── api/              # FastAPI web layer (routes, middleware, deps)
├── services/         # Async business logic (chat, workflow, optimization)
├── workflows/        # 5-phase orchestration pipeline
├── dspy_modules/     # DSPy signatures, reasoner, GEPA optimization
├── agents/           # Microsoft Agent Framework integration
├── tools/            # Tool adapters (Tavily, browser, MCP)
├── utils/            # Infrastructure (cfg/, infra/, storage/)
├── models/           # Shared Pydantic schemas
├── evaluation/       # Batch evaluation and metrics
└── config/           # workflow_config.yaml (source of truth)
```

## Key Technologies

- **Backend**: Python 3.12+, FastAPI, Typer
- **Frontend**: Vite + React 19 + Tailwind
- **AI/Agents**: DSPy, Microsoft Agent Framework, ChromaDB (for memory)
- **Package Manager**: `uv` (Python), `npm` (Frontend)

## Development Workflows

- **Run Backend**: `make run`
- **Run Dev Servers**: `make dev`
- **Test**: `make test`

## Conventions

- Use `uv run` for Python commands.
- Config is in `src/agentic_fleet/config/workflow_config.yaml`.
- Logs and runtime data are in `.var/`.
