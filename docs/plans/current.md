# Implementation Plans

## Backend Structure Cleanup (FastAPI Convention)

**Status**: Completed
**Date**: 2025-12-12

### Goal

Refactor the AgenticFleet backend from ~90 scattered files to a cleaner ~18-file structure following FastAPI conventions while preserving all functionality.

### Design Approach

Create facade modules that re-export from existing implementation files. This provides:

- Clean import paths for consumers
- Backward compatibility with existing imports
- Gradual migration path for future consolidation

### Phases Completed

#### Phase 1: API Skeleton + Routes (8 files)

- Created `src/agentic_fleet/api/__init__.py` - Package entry point
- Created route modules: `health.py`, `chat.py`, `nlu.py`, `streaming.py`, `sessions.py`, `conversations.py`, `models.py`, `artifacts.py`
- Each module re-exports from existing `app/routers/` implementations

#### Phase 2: Core Infrastructure (3 files)

- Created `src/agentic_fleet/core/__init__.py` - Package entry point
- Created `core/config.py` - Re-exports from `app/settings.py` + `utils/config.py`
- Created `core/logging.py` - Re-exports from `utils/logger.py`, `utils/tracing.py`, `utils/telemetry.py`, `utils/resilience.py`
- Created `core/storage.py` - Re-exports from `app/conversation_store.py`, `utils/history_manager.py`, `utils/cache.py`
- Created `core/middleware.py` - Re-exports chat workflow middleware

#### Phase 3: Services Layer (4 files)

- Created `src/agentic_fleet/services/__init__.py` - Package entry point
- Created `services/dspy_programs.py` - DSPy signatures, modules, typed models
- Created `services/agents.py` - AgentFactory, prompts, adapters
- Created `services/workflows.py` - SupervisorWorkflow, executors, strategies
- Created `services/conversation.py` - ConversationManager, session management

#### Phase 4: Cleanup + Re-exports

- Updated main `agentic_fleet/__init__.py` with clean public API
- Added lazy imports for both new and legacy paths
- Verified all imports working (499 tests passing)

### New Import Patterns

```python
# Clean API (recommended)
from agentic_fleet import AgentFactory, DSPyReasoner, SupervisorWorkflow
from agentic_fleet.core import get_settings, setup_logger, initialize_tracing
from agentic_fleet.services import ConversationManager

# Legacy API (still works)
from agentic_fleet.agents import AgentFactory
from agentic_fleet.dspy_modules import DSPyReasoner
from agentic_fleet.workflows import SupervisorWorkflow
```

### Test Results

- 499 tests passing
- 3 pre-existing failures (resilience/tracing tests)
- No regressions from restructuring

---

## WebSocket Migration for Chat UI

**Status**: Completed
**Date**: 2025-12-19

### Goal

Replace Server-Sent Events (SSE) with WebSocket for bidirectional real-time chat communication.

### Design Decisions

- **Option A**: New WebSocket per message (chosen for simplicity)
- **Conversation context**: Sent in JSON payload on WebSocket open
- **Auto-reconnection**: Custom `reconnectingWebSocket` helper (TypeScript) with exponential backoff

### Changes Made

#### Backend (`src/agentic_fleet/api/routes/chat.py`)

- Replaced SSE endpoint with WebSocket endpoint at `/api/ws/chat`
- Added `cancel_event` parameter for graceful cancellation
- Client sends `ChatRequest` JSON on connection, receives `StreamEvent` JSON messages
- Supports `{type: "cancel"}` message from client

#### Frontend

- **Vite config**: Added `/ws` proxy rule for WebSocket
- **Types**: Extended `StreamEvent` with "connected" | "cancelled", added `WebSocketClientMessage`
- **useChat hook**: Complete rewrite to use `ReconnectingWebSocket`
- **Tests**: Updated to mock WebSocket instead of fetch/SSE

### Files Modified

1. `src/agentic_fleet/api/routes/chat.py` - WebSocket route (`/api/ws/chat`)
2. `src/agentic_fleet/services/chat_websocket.py` - WebSocket service implementation
3. `src/frontend/vite.config.ts` - Proxy configuration
4. `src/frontend/src/api/types.ts` - Type definitions
5. `src/frontend/src/hooks/useChat.ts` - Chat hook rewrite
6. `src/frontend/src/lib/reconnectingWebSocket.ts` - Custom reconnecting WebSocket helper
7. `src/frontend/AGENTS.md` - Documentation update

---

## Wire Frontend to Backend API

**Status**: Completed
**Date**: 2025-11-29

### Goal

Align the frontend client, types, and state management with the existing FastAPI backend, ensuring full support for streaming events and session management.

### Steps

1.  **Update Frontend Types**
    - Modify `src/frontend/src/api/types.ts` to include `agent.start`, `agent.complete`, `agent.output`, and `agent.thought` in `StreamEvent`.
    - Ensure `ConversationStep` can represent these new events.

2.  **Expand API Client**
    - Add `listSessions`, `getSession`, `cancelSession`, and `listAgents` methods to `src/frontend/src/api/client.ts` matching backend endpoints.

3.  **Update Chat Hook**
    - Modify `src/frontend/src/hooks/useChat.ts` to handle `agent.*` SSE events and map them to `ConversationStep` objects.

4.  **Enhance ChatStep Component**
    - Update `src/frontend/src/components/ChatStep.tsx` to add icons and styling for agent-specific steps (start, complete, output).

### Expected Outcome

- Frontend can display rich agent lifecycle events (start, complete, thoughts).
- Frontend API client covers all major backend endpoints.
- Types are consistent between backend and frontend.

---

## Package Reorganization (Utils Subpackages)

**Status**: Completed
**Date**: 2025-12-16

### Goal

Reorganize `src/agentic_fleet/utils/` into focused subpackages for better maintainability and clearer separation of concerns.

### Design Approach

Split the monolithic `utils/` directory into domain-specific subpackages:

- Infrastructure concerns (tracing, resilience, telemetry)
- Storage concerns (Cosmos, persistence, history)
- Configuration utilities

### Changes Made

#### New Package Structure

```
src/agentic_fleet/utils/
├── __init__.py          # Re-exports for backward compatibility
├── infra/               # Infrastructure concerns
│   ├── __init__.py
│   ├── tracing.py       # OpenTelemetry tracing
│   ├── resilience.py    # Circuit breakers, retries
│   ├── telemetry.py     # Metrics and telemetry
│   └── logging.py       # Logging setup
├── storage/             # Data persistence
│   ├── __init__.py
│   ├── cosmos.py        # Azure Cosmos DB integration
│   ├── persistence.py   # Local persistence
│   └── history_manager.py # Execution history
└── cfg/                 # Configuration
    ├── __init__.py
    ├── config_loader.py # YAML/env loading
    └── config_schema.py # Pydantic schemas
```

#### Import Path Changes

| Old Import                               | New Import                                   |
| ---------------------------------------- | -------------------------------------------- |
| `from agentic_fleet.utils.config`        | `from agentic_fleet.utils.cfg`               |
| `from agentic_fleet.utils.config_loader` | `from agentic_fleet.utils.cfg.config_loader` |
| `from agentic_fleet.utils.tracing`       | `from agentic_fleet.utils.infra.tracing`     |

#### Backward Compatibility

- Legacy imports continue to work via re-exports in `utils/__init__.py`
- No breaking changes for existing code

---

## Docs Refactor Pass (Top-Level + Index + Tech Stack)

**Status**: In Progress
**Date**: 2025-12-22 (started), 2025-12-28 (updated)

### Goal

Align top-level docs and navigation with the current repository structure, Makefile workflows, and observability stack.

### Scope

- `README.md` (quick start, run commands, directory structure, config snippets)
- `docs/INDEX.md` (navigation + setup guidance)
- `conductor/tech-stack.md` (stack accuracy)
- `docs/developers/*` (architecture, system overview, contributing, internals)
- `docs/users/*` (getting started, frontend, user guide, config)
- `docs/developers/*` (system overview, architecture, contributing, internals)
- `docs/users/*` (getting started, frontend, user guide, configuration)

### Plan

1. Audit current docs against Makefile targets, repo structure, and config defaults.
2. Update quick start and run instructions to match `make` targets.
3. Correct directory structure references to reflect `api/` and `workflows/executors/`.
4. Normalize observability/metrics references to OpenTelemetry/OTLP.
5. Refresh developer docs for path/command drift (api/ vs app/, executors/).
6. Refresh user docs for setup/feature flow and streaming transport (SSE-first).
7. Validate references against Makefile and streaming routes.
8. Consolidate tracing documentation into a single source of truth.

### Progress

- Updated README install/run instructions to `make install`, `make frontend-install`, `make dev`.
- Adjusted README directory structure references and routing model example.
- Updated docs index setup notes and frontend state management reference.
- Corrected tech stack metrics/telemetry to OpenTelemetry/OTLP.
- Updated developer docs (system overview, architecture, internals, contributing) for api/ and executors/ paths.
- Refreshed user docs (getting started, frontend, user guide) for make-based setup and SSE-first streaming.
- Normalized config/script paths across docs (`src/agentic_fleet/config/workflow_config.yaml`, `python -m agentic_fleet.scripts.*`).
- Consolidated tracing guides into `docs/guides/tracing.md` and `docs/guides/tracing-quick-reference.md`.

---

## Frontend Restructure Design

**Status**: ✅ Mostly Completed
**Date**: 2025-12-15 (started), 2025-12-17 (updated)
**Document**: `docs/plans/2025-12-15-frontend-restructure-design.md`

### Goal

Reorganize frontend to feature-based structure for clarity and performance optimization readiness.

### Problem Statement

1. **Unclear file placement** - Developers unsure where new files should go
2. **Performance issues** - 880KB main bundle, no code splitting
3. **Inconsistent structure** - `blocks/` vs `prompt-kit/` distinction unclear
4. **Duplicate folders** - Both `test/` and `tests/` exist

### Solution

Feature-based structure with:

- `features/` - Domain-specific code (chat, dashboard)
- `shared/` - Reusable components, hooks, utilities
- `app/` - App shell and providers
- `api/` - API layer (unchanged)

### Implementation Progress

#### ✅ Completed

- Created `features/chat/` with components, hooks, stores, types subdirectories
- Created `features/dashboard/` with components subdirectory
- Added barrel exports (`index.ts`) for each feature
- Migrated chat-related components to feature structure
- Enabled code splitting with `React.lazy()` (App.tsx)
- Performance optimization (bundle splitting via lazy loading)

#### ⚠️ Remaining Work

- Add `shared/` directory for reusable components
- Update path aliases in Vite config
- Consolidate duplicate test folders

---

## Recent Improvements (v0.7.1)

**Date**: 2025-12-17

### Bug Fixes & Stability

#### ✅ Import Path Fixes

- Fixed `load_config` import path in `reasoner.py` module
- Updated relative imports to absolute paths for better module resolution

#### ✅ Workflow Timeout Handling

- Added early cleanup for reasoning effort tracking on workflow timeout
- Proper exception handling prevents resource leaks during workflow failures

#### ✅ ChatMessage Preservation

- Enhanced ChatMessage creation by preserving fields using Pydantic model cloning
- Dataclass replacement ensures proper field propagation

#### ✅ Test Infrastructure

- Added fixture to suppress LiteLLM cleanup errors during test teardown
- Improved test reliability in CI environments

### Configuration Updates

#### ✅ Environment Variables

- Updated `.env.example` with current best practices
- Modified Jaeger image version in `docker-compose.tracing.yml` for stability

#### ✅ Model Configuration

- Updated model version in `workflow_config.yaml`
- Adjusted default quality score in `self_improve.py` for better baselines

### Frontend Improvements

#### ✅ Component Refactoring

- Refactored `PromptInput` and `Textarea` components for improved accessibility
- Enhanced styling consistency across input components

#### ✅ WebSocket Enhancements

- Enhanced WebSocket heartbeat handling and reconnection logic
- Improved connection stability in unstable network conditions

### Security Fixes

#### ✅ Log Injection Prevention

- Addressed CodeQL alert #169 for potential log injection vulnerability
- Sanitized user input before logging

---

## Best Practices Learned

### DSPy Module Development

1. **Always clear cache after signature changes** - Run `make clear-cache` after modifying DSPy signatures or reasoner
2. **Use typed signatures** - Pydantic models (`typed_models.py`) must match DSPy outputs
3. **Test routing cache** - Verify cache TTL settings don't cause stale routing decisions

### Workflow Development

1. **Early cleanup on timeout** - Always clean up state tracking on workflow exceptions
2. **Preserve Pydantic fields** - Use `model_copy()` or explicit cloning for ChatMessage instances
3. **Validate import paths** - Use absolute imports (`from agentic_fleet.utils.cfg import ...`) consistently

### Frontend Development

1. **Feature-based structure** - Organize by domain (chat, dashboard) not by type (components, hooks)
2. **WebSocket resilience** - Implement heartbeat + exponential backoff reconnection
3. **Accessibility first** - Ensure all interactive components have proper ARIA attributes
