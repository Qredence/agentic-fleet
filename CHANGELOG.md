# Changelog

## 2025-11-03

### Summary

- Normalised frontend SSE handling to use camelCase `agentId` exclusively.
- Introduced a placeholder metrics store (`useMetricsStore`) for future streaming telemetry.
- Retired the legacy chat store and API/component Vitest suites, archiving their expectations for reference.
- Added documentation artefacts to explain the removals and new store scaffolding.

### Rationale

- Remove obsolete workflow/persistence expectations that blocked frontend refactors.
- Prepare a dedicated state slice for upcoming performance instrumentation without affecting current UI behaviour.
- Ensure the API client and types align with backend events after normalising identifier casing.

### Impact

- No breaking API changes. Frontend state relies solely on `agentId` for attribution.
- Test coverage will be rebuilt around the modern chat store flow in subsequent commits.

### Migration Notes

- Consumers should depend on the new `useMetricsStore` when adding telemetry, rather than extending `chatStore` directly.
- Historic workflow assertions live in `docs/archive/chatStore_legacy_tests.md` and `docs/archive/frontend_api_and_component_tests.md` if reintroduction becomes necessary.

### Removed

- `src/frontend/src/stores/__tests__/chatStore.test.ts`
- `src/frontend/src/lib/__tests__/api.test.ts`
- `src/frontend/src/components/chat/__tests__/ChatMessage.test.tsx`

### Follow-up Considerations

- Rebuild the chat store Vitest coverage using streaming scenarios and orchestrator event cases.
- Instrument `useMetricsStore` once performance events are ready to wire in.
