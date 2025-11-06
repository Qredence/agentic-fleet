# Changelog

## v0.5.7 (2025-11-05)

### Highlights

- **Prompt Kit Integration**: Implemented official Prompt Kit Reasoning and ChainOfThought components for proper AI interface patterns
- **Enhanced Orchestrator Visualization**: Chain-of-thought steps now use collapsible Prompt Kit components with icons and improved UX
- **Reasoning Token Support**: Added type definitions and component infrastructure for future o1/o3 reasoning token display
- **Frontend Quality**: Fixed linting issues and improved TypeScript type safety

### Changes

#### Frontend Components

- **ChainOfThought Component**: Replaced custom SystemMessage-based implementation with Prompt Kit ChainOfThought
  - Collapsible steps with icons (ListChecks, Clock, Lightbulb, Info)
  - Auto-expands latest step by default
  - Maps orchestrator message kinds (task_ledger, progress_ledger, facts) to appropriate icons and labels
  - Better visual hierarchy with border and card styling

- **ReasoningDisplay Component**: Enhanced to support two modes
  - Section-based: Multiple reasoning sections from orchestrator (existing)
  - Content-based: Raw reasoning content from o1/o3 models (new)
  - Auto-close behavior when streaming completes via `isStreaming` prop
  - Markdown rendering support with truncation

#### Type System Updates

- Added `reasoning` and `reasoningStreaming` fields to `ChatMessage`
- Extended `SSEEventType` with `reasoning.delta` and `reasoning.completed`
- Updated `SSEEvent` interface to include optional `reasoning` field
- Type-safe imports fixed in markdown.tsx using `type` keyword

#### Prompt Kit Components

- Installed official Prompt Kit Reasoning component via shadcn CLI
- Installed official Prompt Kit ChainOfThought component via shadcn CLI
- Fixed components.json to remove unsupported `registries` field
- Updated response-stream.tsx with proper hook dependency and lint exemptions

### Technical Details

- Backend already configures `reasoning_effort` and `reasoning_verbosity` for o1/o3 models
- Reasoning tokens not yet exposed in SSE events (planned enhancement)
- Frontend infrastructure ready for reasoning token display when backend support is added
- Components follow Prompt Kit patterns for auto-close, collapsibility, and markdown rendering

### Quality Improvements

- Fixed ESLint warnings: added `onError` to useCallback dependencies
- Fixed TypeScript verbatimModuleSyntax error in markdown.tsx
- Added lint exemption for response-stream.tsx hook/component co-location
- All frontend builds passing cleanly

### Testing

- Frontend linting clean (no errors)
- TypeScript compilation successful
- Production build completed successfully (4.13s)

### Future Enhancements

- Expose o1/o3 reasoning tokens in backend SSE events
- Add reasoning.delta and reasoning.completed event handlers
- Wire reasoning content to ReasoningDisplay content mode
- Consider performance optimizations for large reasoning traces

### Documentation

- ReasoningDisplay includes comprehensive JSDoc with usage examples
- ChainOfThought documented with Prompt Kit component patterns
- Type definitions include reasoning field descriptions

## v0.5.6 (2025-11-05)

### Highlights

- **Improved Magentic Workflow Responsiveness**: Aligned multi-agent orchestration streaming with fast-path responsiveness patterns
- **Accumulated Content Tracking**: Both workflows now track and report accumulated content in delta events for better frontend state management
- **Enhanced Logging**: Added detailed workflow execution logs with timing metrics for performance monitoring

### Changes

#### Magentic Workflow Improvements

- Added accumulated content tracking in `MagenticFleetWorkflow.run()` to match fast-path behavior
- Implemented per-agent content buffering for better agent transition tracking
- Enhanced progress events with accumulated content metadata
- Added `agent_accumulated` field to delta events for per-agent content tracking
- Improved logging with workflow start/completion messages and metrics
- Consistent error handling with detailed error messages matching fast-path pattern

#### Fast-Path Workflow

- Migrated from raw `AsyncOpenAI` to agent-framework's `OpenAIResponsesClient`
- Updated to use proper agent-framework types: `ChatMessage`, `ChatOptions`, `TextContent`
- Removed unsupported parameters for gpt-5-mini compatibility
- Updated all tests to work with new client structure

### Technical Details

- `accumulated` field: Global content accumulation across all agents
- `agent_accumulated` field: Per-agent content accumulation
- Progress events now include accumulated content on agent completion
- Both workflows emit consistent event structures for frontend consumption

### Testing

- All 96 workflow and event-related tests passing
- 32 fast-path tests passing (11 unit + 7 integration + 14 classifier)
- Updated test fixtures to use actual agent-framework types

### Performance

- Zero-copy event passthrough maintained
- Immediate yielding without buffering
- Detailed timing logs for TTFT and total workflow duration

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
