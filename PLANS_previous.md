# AgenticFleet Backend Restructure Plan

> **Goal**: Simplify backend from ~90 files to ~18 files following FastAPI template conventions while preserving DSPy/agent architecture.

## Progress Overview

| Phase | Description                  | Status      | Files     |
| ----- | ---------------------------- | ----------- | --------- |
| 1     | Create API skeleton + routes | ✅ Complete | 8 created |
| 2     | Consolidate core/            | ✅ Complete | 3 created |
| 3     | Build services/              | ✅ Complete | 4 created |
| 4     | Cleanup old directories      | ✅ Complete | -         |

---

## Target Structure

```
src/agentic_fleet/
├── __init__.py
├── main.py                 # FastAPI app entrypoint
├── api/                    # FastAPI router layer
│   ├── __init__.py
│   ├── main.py             # Router aggregation
│   ├── api_v1/
│   │   └── api.py           # Versioned router aggregation
│   ├── deps.py             # Dependency injection
│   └── routes/
│       ├── chat.py         # WebSocket streaming
│       ├── workflows.py    # /run
│       ├── sessions.py     # /sessions
│       ├── history.py      # /history
│       ├── dspy.py         # /dspy/*
│       ├── nlu.py          # /classify_intent, /extract_entities
│       ├── conversations.py
│       └── agents.py
├── core/                   # Infrastructure
│   ├── __init__.py
│   ├── config.py           # Settings + workflow config
│   ├── logging.py          # Logger + telemetry
│   └── storage.py          # File/DB persistence
├── services/               # Business logic
│   ├── __init__.py
│   ├── dspy_programs.py    # DSPy signatures, modules, programs
│   ├── agents.py           # Agent definitions + factory
│   ├── workflows.py        # Workflow orchestration
│   └── conversation.py     # Conversation management
│   └── chat_websocket.py   # WebSocket chat service implementation
├── tools/                  # External integrations
│   └── (existing tools)
└── cli/                    # CLI entry point
    └── main.py
```

---

## Phase 1: Create API Skeleton + Routes ✅

**Status**: Complete
**Date**: 2025-12-11

### Tasks

- [x] Create `api/` and `services/` directories
- [x] Create `api/__init__.py` - package exports
- [x] Create `api/main.py` - router aggregation
- [x] Create `api/deps.py` - dependency injection facade
- [x] Create `api/routes/__init__.py`
- [x] Create `api/routes/chat.py` - WebSocket streaming endpoint
- [x] Create `api/routes/workflows.py` - workflow execution endpoint (/run)
- [x] Create `api/routes/conversations.py` - conversations CRUD endpoints
- [x] Create `api/routes/agents.py` - agent listing endpoint
- [x] Create `services/__init__.py` - placeholder
- [x] Fix duplicate `/agents` route
- [x] Update test imports (`schemas` → `models`)

### Files Created

```
src/agentic_fleet/api/__init__.py
src/agentic_fleet/api/deps.py
src/agentic_fleet/api/main.py
src/agentic_fleet/api/routes/__init__.py
src/agentic_fleet/api/routes/agents.py
src/agentic_fleet/api/routes/chat.py
src/agentic_fleet/api/routes/conversations.py
src/agentic_fleet/api/routes/workflows.py
src/agentic_fleet/services/__init__.py
```

### Verification

- ✅ All imports work (`uv run python -c "from agentic_fleet.api import api_router"`)
- ✅ Type checking passes (`uv run ty check src/agentic_fleet/api/`)
- ✅ 48/53 tests pass (5 pre-existing lifespan errors)
- ✅ Routes correctly registered: `/run`, `/sessions/*`, `/history/*`, `/agents`, `/conversations/*`, `/ws/chat`

---

## Phase 2: Consolidate core/ ✅

**Status**: Complete
**Date**: 2025-12-12

### Tasks

- [x] Create `core/config.py` - re-exports from utils/config.py + app/settings.py
- [x] Create `core/logging.py` - re-exports from utils/logger.py, tracing.py, telemetry.py, resilience.py
- [x] Create `core/storage.py` - re-exports from app/conversation_store.py, utils/history_manager.py, utils/cache.py
- [x] Update `core/__init__.py` with lazy imports for commonly used items
- [x] Fix test import (`core.middlewares` → `core.middleware`)

### Files Created

```
src/agentic_fleet/core/config.py    # Unified config access
src/agentic_fleet/core/logging.py   # Logging + tracing + resilience
src/agentic_fleet/core/storage.py   # Storage + caching
```

### Verification

- ✅ All imports work:
  ```python
  from agentic_fleet.core.config import get_settings, load_workflow_config, env_config
  from agentic_fleet.core.logging import setup_logger, initialize_tracing
  from agentic_fleet.core.storage import ConversationStore, HistoryManager, TTLCache
  ```
- ✅ Type checking passes (`uv run ty check src/agentic_fleet/core/`)
- ✅ 499/507 tests pass (3 pre-existing failures, 5 pre-existing lifespan errors)

### Architecture Note

Phase 2 creates **facade modules** that re-export from existing locations. This approach:

- Provides a clean new API (`core.config`, `core.logging`, `core.storage`)
- Maintains backward compatibility (original files unchanged)
- Defers full consolidation to Phase 4 cleanup

---

## Phase 3: Build services/ ✅

**Status**: Complete
**Date**: 2025-12-12

### Tasks

- [x] Create `services/dspy_programs.py` - DSPy signatures, typed models, assertions, NLU
- [x] Create `services/agents.py` - AgentFactory, DSPyEnhancedAgent, prompts
- [x] Create `services/workflows.py` - SupervisorWorkflow, executors, strategies, models
- [x] Create `services/conversation.py` - ConversationManager, WorkflowSessionManager
- [x] Update `services/__init__.py` - lazy imports for commonly used items

### Files Created

```
src/agentic_fleet/services/dspy_programs.py   # DSPy signatures, modules, typed models, assertions
src/agentic_fleet/services/agents.py          # Agent factory, DSPyEnhancedAgent, prompts
src/agentic_fleet/services/workflows.py       # Workflow orchestration, executors, strategies
src/agentic_fleet/services/conversation.py    # Conversation & session management
```

### Verification

- ✅ All imports work:
  ```python
  from agentic_fleet.services.dspy_programs import DSPyReasoner, TaskAnalysis, FleetReAct
  from agentic_fleet.services.agents import AgentFactory, get_planner_instructions
  from agentic_fleet.services.workflows import SupervisorWorkflow, create_supervisor_workflow
  from agentic_fleet.services.conversation import ConversationManager, WorkflowSessionManager
  from agentic_fleet.services import AgentFactory, DSPyReasoner, SupervisorWorkflow
  ```
- ✅ Type checking passes (`uv run ty check src/agentic_fleet/services/`)
- ✅ 499/507 tests pass (3 pre-existing failures, 5 pre-existing lifespan errors)

### Key Exports

**services/dspy_programs.py**:

- `DSPyReasoner`, `TaskAnalysis`, `TaskRouting`, `QualityAssessment`
- `FleetReAct`, `FleetPoT`, `HandoffDecision`, `HandoffProtocol`
- `RoutingDecisionOutput`, `TaskAnalysisOutput`, `QualityAssessmentOutput`
- `assert_valid_agents`, `suggest_task_type_routing`, `validate_routing_decision`

**services/agents.py**:

- `AgentFactory`, `DSPyEnhancedAgent`, `FoundryAgentAdapter`
- `get_planner_instructions`, `get_coder_instructions`, `get_verifier_instructions`

**services/workflows.py**:

- `SupervisorWorkflow`, `create_supervisor_workflow`, `WorkflowConfig`
- `AnalysisExecutor`, `RoutingExecutor`, `ExecutionExecutor`, `ProgressExecutor`
- `execute_delegated`, `execute_parallel`, `execute_sequential`
- `HandoffManager`, `HandoffContext`, `DSPyGroupChatManager`

**services/conversation.py**:

- `ConversationManager`, `WorkflowSessionManager`, `ConversationStore`
- `Conversation`, `Message`, `MessageRole`, `WorkflowSession`

---

## Phase 4: Cleanup 🔲

**Status**: Complete
**Date**: 2025-12-12

### Tasks

- [x] Update all imports across codebase (remove `agentic_fleet.app.*`)
- [x] Remove deprecated `src/agentic_fleet/app/` package (api-first)
- [x] Update dev entrypoints (`make backend`, `make dev`, scripts) to `agentic_fleet.main:app`
- [x] Update documentation references to new API structure
- [x] Update tests to import `agentic_fleet.main` and `agentic_fleet.api.*`

### Expected Outcome

- Clean directory structure
- No broken imports
- All tests passing
- Documentation reflects new structure

---

## Pre-Cleanup Files Removed (Before Phase 1)

These deprecated files were removed during initial analysis:

| File                  | Reason                                         |
| --------------------- | ---------------------------------------------- |
| `app/schemas.py`      | Deprecated re-export (use `app/models.py`)     |
| `app/dependencies.py` | Deprecated re-export (use `app/dependencies/`) |
| `core/middlewares.py` | Deprecated alias                               |
| `core/converters.py`  | Deprecated alias                               |
| `utils/infra.py`      | Redundant re-export                            |
| `utils/storage.py`    | Redundant re-export                            |
| `utils/cfg/`          | Redundant directory                            |

---

## Notes

- **Breaking change**: `src/agentic_fleet/app/` removed; use `agentic_fleet.main:app` + `agentic_fleet.api.*`
- **HTTP contract**: `/api/v1/*` routes remain stable; streaming stays at `/api/ws/chat`
- **Testing**: Run `make test` after each phase
- **Type checking**: Run `make type-check` after each phase
