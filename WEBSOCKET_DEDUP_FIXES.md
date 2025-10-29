# WebSocket Reconnection & Message Deduplication Fixes

## Problems Fixed

### 1. WebSocket Connecting 36+ Times Per Message

**Root Cause**: The `connect()` function in `useWebSocket.ts` had dependencies on callback functions (`onMessage`, `onOpen`, `onClose`, `onError`). These callbacks change on every parent component render, causing the effect to re-run constantly and spawn new WebSocket connections, which then triggers re-renders, creating an infinite loop.

**Visible Impact**:

- Browser console showed "WebSocket connected" 36+ times on a single message send
- Network tab showed 36+ WebSocket connection attempts to the same URL
- Backend logs showed hundreds of connection open/close events

### 2. Messages Rendering Twice

**Root Cause**: While only one message was being added to state, component re-mounting or state updates during the WebSocket loop caused messages to render multiple times.

**Visible Impact**:

- User sends "hello world" once
- Chat UI shows "hello world" twice
- Console shows message added only once but renders twice

## Solutions Implemented

### File 1: `src/frontend/src/lib/hooks/useWebSocket.ts`

#### Change 1: Added URL & Callback Tracking Refs

```typescript
const currentUrlRef = useRef<string | null>(null);
const callbacksRef = useRef({ onMessage, onOpen, onClose, onError });
```

#### Change 2: Fixed connect() Dependencies

**Before:**

```typescript
const connect = useCallback(() => {
  // ...
}, [
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnectInterval,
  maxReconnectAttempts,
  cleanup,
]);
```

**After:**

```typescript
const connect = useCallback(() => {
  // Skip if already connected to this URL
  if (
    currentUrlRef.current === url &&
    wsRef.current?.readyState === READY_STATE_OPEN
  ) {
    console.debug("[WebSocket] Already connected to", url);
    return;
  }

  // ... connection logic using callbacksRef.current instead of callbacks

  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [url, reconnectInterval, maxReconnectAttempts, cleanup]);
```

**Key Improvements:**

- Removed `onMessage, onOpen, onClose, onError` from dependencies
- Added URL duplicate check using `currentUrlRef`
- Now only depends on stable values and refs

#### Change 3: Use callbacksRef in Handlers

**Before:**

```typescript
ws.onopen = () => {
  onOpen?.();
};
```

**After:**

```typescript
ws.onopen = () => {
  callbacksRef.current.onOpen?.();
};
```

#### Change 4: Added Effect to Sync Callbacks

```typescript
useEffect(() => {
  callbacksRef.current = { onMessage, onOpen, onClose, onError };
}, [onMessage, onOpen, onClose, onError]);
```

This keeps callbacks current without triggering `connect()` to recreate.

### File 2: `src/frontend/src/lib/use-fastapi-chat.ts`

#### Change 1: Added Message ID Set Ref

```typescript
const messageIdSetRef = useRef<Set<string>>(new Set());
```

#### Change 2: Updated addMessage with Set-Based Deduplication

**Before:**

```typescript
const addMessage = useCallback((message: Message) => {
  setMessages((prev) => {
    // Prevent duplicate messages
    if (prev.some((m) => m.id === message.id)) {
      return prev;
    }
    return [...prev, message];
  });
}, []);
```

**After:**

```typescript
const addMessage = useCallback((message: Message) => {
  if (messageIdSetRef.current.has(message.id)) {
    console.warn(`[Dedup] Skipping duplicate message: ${message.id}`);
    return;
  }
  messageIdSetRef.current.add(message.id);
  setMessages((prev) => [...prev, message]);
}, []);
```

**Performance Improvement**: O(n) array check → O(1) Set lookup

#### Change 3: Updated startStreamingMessage with Set-Based Deduplication

```typescript
const startStreamingMessage = useCallback(
  (id: string, content: string, actor?: string) => {
    if (messageIdSetRef.current.has(id)) {
      console.warn(`[Dedup] Skipping duplicate streaming message: ${id}`);
      return;
    }
    const newMessage: Message = {
      id,
      role: "assistant",
      content,
      actor,
    };
    streamingMessageRef.current = newMessage;
    messageIdSetRef.current.add(id);
    setMessages((prev) => [...prev, newMessage]);
  },
  [],
);
```

## Expected Results

### Before Fix

```
Console logs:
- "WebSocket connected" (appears 36+ times)
- "Adding user message" (appears once)

UI Behavior:
- Message: "hello world" appears twice
- "Agent is thinking..." appears multiple times
- Multiple duplicate connections in network tab
```

### After Fix

```
Console logs:
- "[WebSocket] Connecting to ws://localhost:8000/ws/chat/[id]" (appears once)
- "[WebSocket] Connected to ws://localhost:8000/ws/chat/[id]" (appears once)
- "Adding user message" (appears once)
- "[Dedup] Skipping duplicate message: ..." (rare, only if server sends dupes)

UI Behavior:
- Message: "hello world" appears once
- "Agent is thinking..." appears once (when appropriate)
- Single WebSocket connection in network tab
- No error spam in console
```

## Testing the Fix

### Manual Test Steps

1. Open browser DevTools (F12)
2. Go to Console tab
3. Send a message: "hello world"
4. Verify:
   - ✅ Console shows `[WebSocket] Connected to...` only once
   - ✅ Console shows `Adding user message...` only once
   - ✅ Chat displays "hello world" exactly once (not twice)
   - ✅ No `[Dedup] Skipping duplicate` messages (unless server sends dupes)

### Network Tab Verification

1. Open DevTools → Network tab
2. Filter for "WS" (WebSocket)
3. Send a message
4. Verify: Only ONE WebSocket connection to `ws://localhost:8000/ws/chat/[id]`

## Debug Logging Added

New debug statements to track WebSocket behavior:

```typescript
console.debug("[WebSocket] Already connected to", url);
console.debug("[WebSocket] Connecting to", url);
console.debug("[WebSocket] Connected to", url);
console.warn(`[Dedup] Skipping duplicate message: ${message.id}`);
console.warn(`[Dedup] Skipping duplicate streaming message: ${id}`);
```

These are prefixed with `[WebSocket]` or `[Dedup]` for easy filtering in DevTools.

## Technical Details

### Why This Works

1. **URL Tracking** (`currentUrlRef`):
   - Prevents connecting to the same URL twice
   - Check happens before creating new WebSocket: `if (currentUrlRef.current === url && wsRef.current?.readyState === READY_STATE_OPEN) return;`

2. **Stable Dependencies**:
   - `connect()` no longer depends on callbacks, only on stable values
   - Callbacks are kept current via separate `useEffect`, not as dependencies
   - This breaks the dependency cycle that was causing infinite reconnections

3. **Message ID Set**:
   - O(1) lookup is more reliable than O(n) array check
   - Set is cleared never (persists for message history)
   - Acts as a "seen" cache for deduplication

### Edge Cases Handled

1. **Server Sends Duplicate Messages**: Dedup Set catches these
2. **WebSocket Reconnects**: currentUrlRef prevents duplicate connections to same URL
3. **Callback Changes**: New useEffect keeps callbacksRef current without triggering reconnects
4. **Stale Closures**: Using ref callbacks avoids stale function closures

## Files Modified

1. `/src/frontend/src/lib/hooks/useWebSocket.ts` - WebSocket reconnection fix
2. `/src/frontend/src/lib/use-fastapi-chat.ts` - Message deduplication

## No Breaking Changes

These fixes maintain backward compatibility:

- Hook signatures unchanged
- Return types unchanged
- All previous functionality preserved
- Only fixes infinite loops and deduplication
