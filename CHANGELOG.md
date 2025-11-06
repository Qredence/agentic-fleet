# Changelog

## v0.5.9 (2025-11-06) – Schema & Factory Consolidation

### Highlights (v0.5.9)

- **[BREAKING]** Removed 6 duplicate files (~380 lines): `models/chat.py`, `models/entities.py`, `models/responses.py`, `api/workflow_factory.py`, `models/workflow.py`, `api/approvals/schemas.py`
- Consolidated schema imports to canonical API locations: `api.chat.schemas`, `api.entities.schemas`, `api.responses.schemas`, `api.models.workflow_config`
- Migrated all code from legacy `api.workflow_factory.WorkflowFactory` to async-first `utils.factory.WorkflowFactory`
- Added `validate` CLI command for pre-flight configuration checks without execution
- Maintained backward compatibility via `models/__init__.py` re-exports

### Changes (v0.5.9)

#### Backend Consolidation

- **Deleted duplicate schemas**: Removed `models/chat.py`, `models/entities.py`, `models/responses.py` – API schemas in `api/**/schemas.py` are now canonical
- **Deleted legacy factory**: Removed `api/workflow_factory.py` (synchronous implementation) – `utils/factory.py` (async-first) is now canonical
- **Deleted duplicate config**: Removed `models/workflow.py` (7-field) – `api/models/workflow_config.py` (10-field extended version) is now canonical
- **Deleted empty file**: Removed `api/approvals/schemas.py` (contained only docstring)
- **Updated `models/__init__.py`**: Now re-exports from canonical API locations while preserving same `__all__` exports for backward compatibility
- **Migrated imports**: Updated 10 files (console.py, 3 test files, 2 scripts, Makefile, 3 workflow modules, core/**init**.py) to use `utils.factory.WorkflowFactory` and `models.WorkflowConfig`

#### CLI Enhancements

- **New `validate` command**: Pre-flight configuration checks without workflow execution
  - Tests WorkflowFactory instantiation and YAML loading
  - Validates all registered workflows can be instantiated
  - Checks agent configuration resolution
  - Supports `--verbose` flag for detailed debugging
  - Returns exit code 1 on errors, 0 on success/warnings
  - Usage: `uv run fleet validate` or `uv run fleet validate -v`

#### Testing

- Updated 3 test files to use `utils.factory.WorkflowFactory`
- Marked 3 legacy tests as skipped (testing removed `api.workflow_factory` implementation details)
- All 53 affected tests passing, 5 skipped

### Migration Notes (v0.5.9)

**Breaking changes:**

```python
# OLD: Direct imports from models/ submodules (NO LONGER WORKS)
from agentic_fleet.models.chat import ChatRequest
from agentic_fleet.models.workflow import WorkflowConfig
from agentic_fleet.api.workflow_factory import WorkflowFactory

# NEW: Import from models package (backward compatible) or API directly
from agentic_fleet.models import ChatRequest, WorkflowConfig
from agentic_fleet.utils.factory import WorkflowFactory

# OR: Import directly from canonical API locations
from agentic_fleet.api.chat.schemas import ChatRequest
from agentic_fleet.api.models.workflow_config import WorkflowConfig
```

**Import mapping table:**

| Old Import                             | New Canonical Location                      | Re-export Available             |
| -------------------------------------- | ------------------------------------------- | ------------------------------- |
| `models.chat.*`                        | `api.chat.schemas.*`                        | Yes via `models.*`              |
| `models.entities.*`                    | `api.entities.schemas.*`                    | Yes via `models.*`              |
| `models.responses.*`                   | `api.responses.schemas.*`                   | Yes via `models.*`              |
| `models.workflow.WorkflowConfig`       | `api.models.workflow_config.WorkflowConfig` | Yes via `models.WorkflowConfig` |
| `api.workflow_factory.WorkflowFactory` | `utils.factory.WorkflowFactory`             | No (breaking change)            |

**Validation:**

```bash
# Validate configuration health
uv run fleet validate

# Detailed debugging
uv run fleet validate -v
```

### Impact (v0.5.9)

- **Files removed**: 6 (total: 87→81 files, ~7.4% reduction)
- **Lines removed**: ~380 lines
- **Import changes**: 10 files updated
- **Backward compatibility**: Maintained via `models/__init__.py` re-exports (except `WorkflowFactory`)

## v0.5.8 (2025-11-06) – Async Factory & Domain Exceptions (MERGED)

### Highlights (v0.5.7)

- Fixed conversation retrieval bug preventing empty conversations from being loaded
- Implemented full conversation listing functionality via `PersistenceAdapter.list()`
- Added `ConversationRepository.list_all()` for retrieving all conversations
- Conversation history now correctly injects into workflow context for multi-turn interactions
- Added regression test `test_empty_conversation_retrieval()` to prevent future bugs

### Changes (v0.5.7)

#### Backend

- **PersistenceAdapter.get()**: Now checks conversation table first before loading messages, allowing empty conversations to be retrieved
- **PersistenceAdapter.list()**: Fully implemented using `ConversationRepository.list_all()`, returns conversations without loading messages for performance
- **ConversationRepository.list_all()**: New method returning all conversations ordered by `updated_at DESC`
- **Conversation Memory**: History formatted as "ROLE: content" pairs, prepended to current message with format "Previous conversation:\n{history}\n\nUser's current message: {message}"
- **Metadata Extraction**: Conversation title and timestamps now extracted from conversation record instead of first message

#### Tests

- Added `test_empty_conversation_retrieval()` regression test to `test_conversation_memory.py`
- All 18 tests passing (11 persistence + 6 conversation memory + 1 API CRUD)
- End-to-end UI testing verified with Chrome DevTools

#### Docs

- Updated conversation memory implementation notes
- Documented history injection format and workflow integration

### Bug Fixes (v0.5.7)

- Fixed "Conversation not found" error when retrieving newly created conversations before first message
- Fixed conversation listing returning empty results despite existing conversations

### Migration Notes (v0.5.7)

No action required. Existing conversations continue working. New conversations now properly support immediate retrieval.

### Verification (v0.5.7)

Production testing completed:

- Two-turn conversation tested: "What is the Monty Hall problem?" followed by "Why should I switch? Isn't it 50-50 after the host reveals a goat?"
- Backend logs confirmed history injection working correctly
- Agent responses demonstrated full context awareness
- Follow-up questions answered appropriately using previous message context

## v0.5.6 (2025-11-06) – Reasoning Integration

### Highlights (v0.5.6)

- Unified reasoning integration: backend extraction, single SSE emission (`reasoning.completed`), persistence, and dual UI surfaces (Reasoning panel + ChainOfThought).
- Reasoning trace appears before assistant content and is stored with the message for auditability.
- Backward compatible: models without reasoning simply omit the panel; no client changes required.
- Stability: workflow_start timing initialization removes potential elapsed-time inconsistencies in fast-path streaming.

### Changes (v0.5.6)

#### Core Backend

- Added reasoning trace extraction helper in workflow events.
- Emitted a single `reasoning.completed` SSE event prior to assistant message finalization.
- Extended conversation message persistence with optional `reasoning` field (non-breaking).

#### Frontend

- Added transient reasoning state (content + completion) with automatic panel collapse.
- Retained ChainOfThought for structured orchestration; reasoning panel used for model-internal trace.
- Ensured rendering order shows reasoning before assistant message content.

#### Types & Contracts

- Added `reasoning` to serialized messages.
- Registered only final `reasoning.completed` (no incremental streaming events).

#### Documentation

- Consolidated earlier reasoning notes into this single release entry.
- Removed transitional version entries (0.5.7 / 0.5.8) to reduce fragmentation.

### Migration Notes (v0.5.6)

No action required. Reasoning appears only when provided; absence yields unchanged responses.

## v0.5.5 (2025-11-05)

### Highlights (v0.5.5)

- Frontend SSE payloads now expose `agentId` exclusively in camelCase to match backend event schemas.
- New `useMetricsStore` placeholder lays groundwork for upcoming streaming telemetry without impacting current UI flows.
- Documentation refreshed to capture chat store retirement and metrics store hand-off.

### Changes (v0.5.5)

- Normalised Responses event bridge and frontend consumers to rely on camelCase identifiers.
- Archived legacy chat store, API client, and component Vitest suites to unblock modernised coverage.
- Added guidance around metrics store scaffolding and removal rationale to docs set.

### Removed

- `src/frontend/src/stores/__tests__/chatStore.test.ts`
- `src/frontend/src/lib/__tests__/api.test.ts`
- `src/frontend/src/components/chat/__tests__/ChatMessage.test.tsx`

### Migration Notes (v0.5.5)

- Extend telemetry features from new `useMetricsStore` instead of deprecated chat store state.
- Historical assertions remain available under `docs/archive/chatStore_legacy_tests.md` and `docs/archive/frontend_api_and_component_tests.md` for reference.

### Follow-up (v0.5.5)

- Rebuild streaming-focused chat store coverage aligned with new architecture.
- Hook performance event instrumentation into `useMetricsStore` once telemetry pipeline lands.
