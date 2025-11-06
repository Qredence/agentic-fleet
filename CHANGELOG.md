# Changelog

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
