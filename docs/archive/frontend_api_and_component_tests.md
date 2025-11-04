# Archived: Legacy Frontend API & ChatMessage Tests

**Archived on:** 2025-11-03
**Removed from:**

- `src/frontend/src/lib/__tests__/api.test.ts`
- `src/frontend/src/components/chat/__tests__/ChatMessage.test.tsx`

## Rationale

Both suites codified expectations for an earlier HTTP client (`chatApi`) and a presentation layer that no longer exist. The modern frontend streams responses via `streamChatResponse`, depends on camelCase agent identifiers, and renders richer chain-of-thought UX than the original static message component. Keeping the tests in place produced unavoidable failures because the referenced exports were removed weeks ago, and the component props they asserted (`role` badges, retry callbacks, legacy styling) have been superseded by the revamped chat experience.

## Notable Coverage (Excerpt)

```typescript
// api.test.ts
expect(mockFetch).toHaveBeenCalledWith("/v1/chat/completions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    messages: [{ role: "user", content: "Hello!" }],
    model: "magentic_fleet",
    stream: false,
  }),
});
```

```tsx
// ChatMessage.test.tsx
expect(screen.getByText("Assistant")).toBeInTheDocument();
expect(messageElement).toHaveClass("bg-gray-50");
```

## Replacement Strategy

- Rebuild API coverage around the new REST endpoints (`/conversations`, `/chat`) and the SSE reader in `streamChatResponse`.
- Add component tests that focus on streaming states, agent attribution, structured content blocks, and accessibility of the redesigned chat UI.
- When telemetry lands, integrate the metrics store into the new coverage rather than reviving these legacy suites.
