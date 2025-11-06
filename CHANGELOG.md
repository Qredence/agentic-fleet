# Changelog

## v0.5.8 (2025-11-06) – Async Factory & Domain Exceptions

### Highlights (v0.5.8)

- **[BREAKING]** Removed legacy `core/` package (10 files), duplicate `workflow.yaml`, `api/responses/models.py`, empty `api/eventing/`, and obsolete `tests/test_magentic_integration.py` – achieving 14% file reduction (94→87 files, ~1,572 lines removed).
- Consolidated imports: `MagenticContext`, `OpenAIResponsesClient` now imported from upstream `agent_framework` instead of local copies.
- Single authoritative `workflows.yaml` now drives configuration (removed workflow.yaml fallback).
- Introduced fully asynchronous `WorkflowFactory.create()` with non-blocking YAML load and DI-friendly singleton (`get_workflow_factory`).
- Added centralized domain exceptions (`api/exceptions.py`) with consistent JSON error envelope: `{"error": {"code": <string>, "message": <string>}}`.
- Replaced all `HTTPException` raises in routes/services with domain exceptions (`WorkflowNotFoundError`, `WorkflowExecutionError`, `EntityNotFoundError`, `ConversationMissingError`, `ValidationError`).
- Eliminated all `@no_type_check` decorators – routes now have explicit type hints ready for strict mypy.
- Consolidated Responses streaming models into a single module (`responses/schemas.py`); removed `responses/models.py`.
- Added Pydantic v2 models for Entities (`EntityListResponse`, `EntityDetailResponse`) and Conversations (`MessageResponse`, `ConversationResponse`, `ConversationsListResponse`).
- Converted remaining synchronous endpoints (system health, approvals submission) to `async` functions.
- Normalized conversation and entity endpoints to structured response models (no manual dict serialization helpers).

### Changes (v0.5.8)

#### Backend Architecture

- **Consolidation**: Removed `core/` shim layer (10 files), `workflow.yaml`, `api/responses/models.py`, empty `api/eventing/`, obsolete `test_magentic_integration.py`.
- **Upstream imports**: `MagenticContext`, `OpenAIResponsesClient` imported from `agent_framework` package.
- `utils/factory.py`: Async construction (`create()`), singleton helpers (`get_workflow_factory`, `get_workflow_factory_cached`) and default workflow fallback semantics preserved.
- `api/workflow_factory.py`: Simplified resolution order to only check workflows.yaml (removed workflow.yaml fallback).
- `api/app.py`: Registers domain exception handlers during app creation via `register_exception_handlers(app)`.
- `api/exceptions.py`: Provides base `AgenticFleetException` + specialized subclasses; adds automatic handler registration loop.
- `api/workflows/routes.py`: Raises `WorkflowNotFoundError` / `WorkflowExecutionError` instead of raw HTTP errors; streaming and status endpoints updated accordingly.
- `api/entities/schemas.py`: Replaced `EntityInfo` / `DiscoveryResponse` with `EntityDetailResponse` / `EntityListResponse` (extra fields allowed via `extra="allow"`).
- `api/conversations/routes.py`: Refactored to use Pydantic models (removed custom serializer functions) with explicit `response_model` declarations.
- `api/responses/schemas.py`: Merged streaming event classes (Delta, Completed, Orchestrator) alongside request/complete schemas (removed duplicate models.py).
- `api/chat/service.py`: Emits `WorkflowExecutionError` on failure instead of `HTTPException`.
- Removed all `@no_type_check` decorators across API modules for stricter typing.

#### Error Handling

- Unified envelope: Example 404 workflow error → `{"error": {"code": "workflow_not_found", "message": "Workflow 'abc' not found"}}`.
- Validation issues (e.g. missing input) now emit `validation_error` (status 400).
- Legacy `ConversationNotFoundError` mapped to new JSON format transparently.

#### Testing

- Updated `test_chat_schema_and_workflow.py` to expect `WorkflowExecutionError` instead of `HTTPException` for failing workflow execution path.
- Streaming, entity, and conversation tests pass against new Pydantic schemas (subset run: 34 tests green).
- Backward-compatible synchronous factory constructor retained temporarily; full migration to async usage planned in follow-up (Task 15).

### Migration Notes (v0.5.8)

Breaking/API-visible changes:

1. **Removed `core/` package**: Update imports:
   - `from agentic_fleet.core.agents` → `from agentic_fleet.agents.coordinator`
   - `from agentic_fleet.core.events` → `from agentic_fleet.models.events` or `from agent_framework`
   - `from agentic_fleet.core.tools` → `from agentic_fleet.tools.registry`
   - `from agentic_fleet.core.magentic_framework import MagenticContext` → `from agent_framework import MagenticContext`
2. **Configuration**: Remove references to `workflow.yaml` (singular) – only `workflows.yaml` is recognized.
3. Error response shape changed (was `{"detail": "..."}` for HTTPException, now structured `{"error": {"code": "...", "message": "..."}}`). Update clients parsing error details.
4. Entity models renamed: replace `EntityInfo` → `EntityDetailResponse`, `DiscoveryResponse` → `EntityListResponse`.
5. Conversation endpoints now return typed models; any code expecting raw dict keys should adapt to identical field names but may benefit from schema validation.
6. Responses streaming model imports: use `from agentic_fleet.api.responses.schemas import ResponseDeltaEvent` (models module removed).
7. Prefer `await get_workflow_factory()` in async contexts; direct `WorkflowFactory()` construction is deprecated and will be removed.

Regex-assisted refactors (examples):

```bash
# Replace HTTPException instantiations (manual review recommended)
grep -R "HTTPException" -l src | xargs sed -E -i '' 's/HTTPException\((status_code=)?500[^)]*\)/WorkflowExecutionError("An error occurred while processing your request")/g'

# Entity model rename
grep -R "EntityInfo" -l src | xargs sed -E -i '' 's/EntityInfo/EntityDetailResponse/g'
grep -R "DiscoveryResponse" -l src | xargs sed -E -i '' 's/DiscoveryResponse/EntityListResponse/g'
```

### Verification (v0.5.8)

- Targeted pytest subset (entities, responses, conversation memory, chat workflow service) passing: 34 tests.
- Chat workflow domain error propagation verified (`WorkflowExecutionError`).
- SSE streaming still emits `response.delta`, `response.completed`, `reasoning.completed`, `[DONE]` markers unchanged.
- Health and approvals endpoints function asynchronously (manual invocation smoke-tested via test clients).

### Follow-up (v0.5.8)

- Migrate all remaining test instantiation sites to async factory (Task 15).
- Enforce mypy strict mode and remove legacy synchronous factory constructor.
- Extend domain exceptions with optional trace IDs for observability once OTEL integration toggled via `ENABLE_OTEL`.
- Add richer validation for entity input schemas (support structured `input` variants).

---

## v0.5.7 (2025-11-06) – Conversation Memory Enhancement

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
