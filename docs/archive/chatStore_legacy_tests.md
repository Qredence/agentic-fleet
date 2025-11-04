# Archived: Legacy Chat Store Tests

**Archived on:** 2025-11-03
**Removed from:** `src/frontend/src/stores/__tests__/chatStore.test.ts`

## Rationale

The former chat store test suite exercised workflow identifiers (`currentWorkflowId`), connection flags (`isConnected`), persistence middleware, and assorted computed selectors that no longer exist in the modern Zustand store. Keeping the suite in place created false negatives and blocked refactors focused on streaming semantics and agent attribution. The runtime no longer exposes those fields, so the tests were retired and archived for historical reference.

## Notable Coverage (Excerpt)

```typescript
describe("initial state", () => {
  it("has correct initial state", () => {
    const { result } = renderHook(() => useChatStore());

    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
    expect(result.current.currentWorkflowId).toBe("magentic_fleet");
    expect(result.current.isConnected).toBe(false);
  });
});
```

```typescript
describe("workflow management", () => {
  it("sets current workflow correctly", () => {
    const { result } = renderHook(() => useChatStore());

    act(() => {
      result.current.setCurrentWorkflow("custom_workflow");
    });

    expect(result.current.currentWorkflowId).toBe("custom_workflow");
  });
});
```

## Replacement Strategy

Future store coverage should concentrate on:

- Streaming delta accumulation and agent switching semantics
- Orchestrator message deduplication
- Completion and error flows
- Performance and telemetry once implemented

When reintroducing workflow or persistence concerns, derive new tests from the current store API rather than reinstating this archived suite.
