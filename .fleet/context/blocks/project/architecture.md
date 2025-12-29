---
label: project-architecture
description: Directory structure, key modules, and component relationships. High-level system map.
limit: 5000
scope: project
updated: 2024-12-29
---

# Project Architecture

## Directory Structure

```
AgenticFleet/
├── src/
│   ├── agentic_fleet/           # Main Python package
│   │   ├── api/                 # FastAPI routes, middleware, deps
│   │   ├── services/            # Business logic layer
│   │   ├── workflows/           # 5-phase orchestration pipeline
│   │   ├── dspy_modules/        # DSPy signatures, reasoner, GEPA
│   │   ├── agents/              # Microsoft Agent Framework
│   │   ├── tools/               # Tool adapters (Tavily, MCP)
│   │   ├── utils/               # Infrastructure utilities
│   │   ├── models/              # Pydantic schemas
│   │   ├── evaluation/          # Batch evaluation
│   │   └── config/              # workflow_config.yaml
│   └── frontend/                # React 19 + Vite + Tailwind
├── tests/                       # Pytest test suite
├── docs/                        # Documentation
├── scripts/                     # Utility scripts
├── .fleet/context/              # Memory system (this!)
└── .var/                        # Runtime data (logs, cache)
```

## Key Modules

### API Layer (`api/`)
- `routes/` - FastAPI endpoints (chat, workflow, nlu)
- `middleware.py` - ChatMiddleware, BridgeMiddleware
- `deps.py` - Dependency injection

### Services Layer (`services/`)
- `chat_service.py` - Conversation management
- `chat_sse.py` / `chat_websocket.py` - Real-time streaming
- `workflow_service.py` - Multi-agent orchestration
- `optimization_service.py` - GEPA optimization jobs

### Workflows (`workflows/`)
- 5-phase pipeline: analysis → routing → execution → progress → quality
- `builder.py` - Workflow construction
- `DSPyGroupChatManager` - Multi-agent discussions

### DSPy Modules (`dspy_modules/`)
- `reasoner.py` - Core reasoning engine
- `nlu.py` - Intent classification, entity extraction
- `typed_models.py` - Pydantic output models
- `assertions.py` - dspy.Assert/Suggest guards

### Configuration
- Source of truth: `src/agentic_fleet/config/workflow_config.yaml`
- Runtime data: `.var/` (logs, cache, history)
