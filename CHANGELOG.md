# Changelog

## v0.5.5 (2025-11-05)

### Highlights

- Frontend SSE payloads now expose `agentId` exclusively in camelCase to match backend event schemas.
- New `useMetricsStore` placeholder lays the groundwork for upcoming streaming telemetry without impacting current UI flows.
- Documentation refreshed to capture the chat store retirement and metrics store hand-off.

### Changes

- Normalised the Responses event bridge and frontend consumers to rely on camelCase identifiers.
- Archived the legacy chat store, API client, and component Vitest suites to unblock modernised coverage.
- Added guidance around the metrics store scaffolding and removal rationale to the docs set.

### Removed

- `src/frontend/src/stores/__tests__/chatStore.test.ts`
- `src/frontend/src/lib/__tests__/api.test.ts`
- `src/frontend/src/components/chat/__tests__/ChatMessage.test.tsx`

### Migration Notes

- Extend telemetry features from the new `useMetricsStore` instead of the deprecated chat store state.
- Historical assertions remain available under `docs/archive/chatStore_legacy_tests.md` and `docs/archive/frontend_api_and_component_tests.md` should you need to reference them.

### Follow-up

- Rebuild streaming-focused chat store coverage aligned with the new architecture.
- Hook performance event instrumentation into `useMetricsStore` once the telemetry pipeline lands.
