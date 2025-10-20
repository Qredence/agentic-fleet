# AGENTS.md - Frontend Development

> **Agent instructions for working with the AgenticFleet React frontend**

This file provides guidance for AI coding agents working specifically within the `src/frontend/` React application. For general project instructions, see the [root AGENTS.md](../../AGENTS.md).

---

## Frontend Overview

The AgenticFleet frontend is a React 19 + TypeScript + Vite application using shadcn/ui components and Tailwind CSS. It provides a chat interface for interacting with the multi-agent workflow system via SSE (Server-Sent Events) streaming.

### Tech Stack

- **Framework**: React 19.2.0
- **Build Tool**: Vite 7.1.10
- **Language**: TypeScript 5.9.3
- **UI Library**: shadcn/ui (Radix UI primitives)
- **Styling**: Tailwind CSS 4.1.14
- **Testing**: Vitest 3.2.4 + Testing Library
- **State Management**: Zustand 5.0.8
- **Markdown**: react-markdown + remark plugins
- **Package Manager**: npm

---

## Project Structure

```
src/frontend/
├── src/
│   ├── App.tsx                        # Main application entry
│   ├── main.tsx                       # React root mount
│   ├── index.css                      # Global styles + Tailwind
│   ├── components/
│   │   ├── agenticfleet-chatbot.tsx  # Main chat component
│   │   └── ui/                       # shadcn/ui components
│   │       ├── avatar.tsx
│   │       ├── button.tsx
│   │       ├── tooltip.tsx
│   │       └── ...
│   ├── lib/
│   │   ├── use-fastapi-chat.ts       # SSE streaming hook (CORE)
│   │   └── utils.ts                  # Utility functions
│   ├── app/                          # Additional app components
│   └── test/                         # Test utilities
├── package.json                       # Dependencies and scripts
├── vite.config.ts                     # Vite configuration
├── tailwind.config.js                 # Tailwind configuration
├── tsconfig.json                      # TypeScript configuration
├── vitest.config.ts                   # Vitest test configuration
└── README.md                          # Frontend-specific docs
```

---

## Development Commands

### Setup

```bash
# Install dependencies (first time)
cd src/frontend
npm install

# Or use make from root
make frontend-install
```

### Development Server

```bash
# Start Vite dev server (port 5173)
npm run dev

# Or use make from root
make frontend-dev

# Full stack development (backend + frontend)
make dev  # From repository root
```

**Dev server features:**

- Hot Module Replacement (HMR) for instant updates
- Proxy configured for `/v1/*` and `/health` → `http://localhost:8000`
- TypeScript type checking in background

### Building

```bash
# Type check
npm run build  # Runs tsc first, then vite build

# Preview production build
npm run preview
```

### Testing

```bash
# Run tests
npm run test

# Run tests in watch mode
npm run test -- --watch

# Run tests with coverage
npm run test -- --coverage
```

### Linting

```bash
# Lint TypeScript/TSX files
npm run lint

# Fix lint errors
npm run lint -- --fix
```

---

## Core Patterns

### SSE Streaming Hook (`lib/use-fastapi-chat.ts`)

**CRITICAL**: This is the heart of the frontend. Never reimplement SSE streaming logic—always use this hook.

```typescript
import { useFastAPIChat } from "@/lib/use-fastapi-chat";

const {
  messages, // Chat message history
  isStreaming, // Is response streaming?
  error, // Error state
  sendMessage, // Send new message
  clearMessages, // Clear history
  retryLastMessage, // Retry failed message
} = useFastAPIChat({
  endpoint: "/v1/responses", // API endpoint
  model: "workflow_as_agent", // Model/workflow name
  workerModel: "gpt-4.1-nano", // Optional: override worker
  reviewerModel: "gpt-4.1", // Optional: override reviewer
});
```

**Hook features:**

- Automatic SSE connection management
- Event parsing (`content_block_delta`, `response_output_item_done`, `approval_required`, `error`)
- Content buffering and delta accumulation
- Reconnection logic
- Error handling
- Message state management

**SSE Event Types:**

```typescript
// Text chunk from agent
{
  "type": "content_block_delta",
  "delta": { "type": "text", "text": "..." }
}

// Message complete
{
  "type": "response_output_item_done",
  "item": { "id": "...", "content": [...] }
}

// HITL approval required
{
  "type": "approval_required",
  "request_id": "...",
  "operation_type": "code_execution",
  "details": { "code": "..." }
}

// Error occurred
{
  "type": "error",
  "error": { "message": "...", "code": "..." }
}
```

### Main Chat Component (`components/agenticfleet-chatbot.tsx`)

Main UI component wrapping the chat interface:

```typescript
import { AgenticFleetChatbot } from "@/components/agenticfleet-chatbot";

function App() {
  return (
    <div className="h-screen">
      <AgenticFleetChatbot />
    </div>
  );
}
```

**Component responsibilities:**

- Render chat messages with markdown
- Handle user input
- Display streaming indicators
- Show approval modals (HITL)
- Error state display

### shadcn/ui Components

All UI components are from shadcn/ui, located in `components/ui/`. These are:

- **Composable**: Built on Radix UI primitives
- **Customizable**: Full control over styling
- **Accessible**: ARIA compliant

**Adding new shadcn/ui components:**

```bash
# Use npx to add components (from frontend directory)
npx shadcn@latest add <component-name>

# Example: Add dialog component
npx shadcn@latest add dialog
```

---

## State Management

### Using Zustand

For complex state, use Zustand stores:

```typescript
import { create } from "zustand";

interface ChatStore {
  conversationId: string | null;
  setConversationId: (id: string) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  conversationId: null,
  setConversationId: (id) => set({ conversationId: id }),
}));
```

### React State Patterns

For component-local state:

```typescript
import { useState, useEffect } from "react";

function MyComponent() {
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Side effects
  }, [dependencies]);
}
```

---

## Styling Guidelines

### Tailwind CSS

Use utility classes for styling:

```tsx
// ✅ CORRECT - Utility classes
<div className="flex items-center gap-2 p-4 bg-gray-100 rounded-lg">
  <span className="text-sm font-medium">Status</span>
</div>

// ❌ WRONG - Inline styles (avoid)
<div style={{ display: 'flex', padding: '16px' }}>
  <span style={{ fontSize: '14px' }}>Status</span>
</div>
```

### Custom Utility Function

Use `cn()` from `lib/utils.ts` for conditional classes:

```typescript
import { cn } from "@/lib/utils";

<div
  className={cn(
    "base-class",
    isActive && "active-class",
    error && "error-class"
  )}
/>;
```

### CSS Variables

Theme variables defined in `index.css`:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --primary: 221.2 83.2% 53.3%;
  /* ... */
}
```

Use via Tailwind:

```tsx
<div className="bg-background text-foreground" />
```

---

## TypeScript Patterns

### Type Safety

Always define types for props and state:

```typescript
// ✅ CORRECT
interface MessageProps {
  content: string;
  role: "user" | "assistant";
  timestamp?: Date;
}

function Message({ content, role, timestamp }: MessageProps) {
  // ...
}

// ❌ WRONG - No types
function Message({ content, role, timestamp }) {
  // ...
}
```

### Event Handlers

Type event handlers properly:

```typescript
import { ChangeEvent, FormEvent } from "react";

function handleSubmit(e: FormEvent<HTMLFormElement>) {
  e.preventDefault();
  // ...
}

function handleChange(e: ChangeEvent<HTMLInputElement>) {
  setValue(e.target.value);
}
```

### Async Functions

```typescript
async function fetchData(id: string): Promise<Data> {
  const response = await fetch(`/api/data/${id}`);
  if (!response.ok) {
    throw new Error("Failed to fetch");
  }
  return response.json();
}
```

---

## API Integration

### Vite Proxy Configuration

Proxy configured in `vite.config.ts`:

```typescript
proxy: {
  "/v1": {
    target: "http://localhost:8000",
    changeOrigin: true,
    timeout: 180000, // 3 minutes
  },
  "/health": {
    target: "http://localhost:8000",
    changeOrigin: true,
  },
}
```

**All API calls to `/v1/*` and `/health` are automatically proxied to the backend.**

### Making API Calls

```typescript
// SSE streaming (use hook)
const { sendMessage } = useFastAPIChat({ endpoint: "/v1/responses" });
sendMessage("Hello");

// Standard POST (non-streaming)
const response = await fetch("/v1/approval/response", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    request_id: "abc123",
    decision: "approve",
  }),
});
```

---

## Testing Patterns

### Component Testing

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Message } from "./message";

describe("Message", () => {
  it("renders user message", () => {
    render(<Message content="Hello" role="user" />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });
});
```

### Hook Testing

```typescript
import { renderHook, act } from "@testing-library/react";
import { useFastAPIChat } from "@/lib/use-fastapi-chat";

describe("useFastAPIChat", () => {
  it("sends message", async () => {
    const { result } = renderHook(() =>
      useFastAPIChat({ endpoint: "/v1/responses" })
    );

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    expect(result.current.messages).toHaveLength(1);
  });
});
```

### Mocking API Calls

```typescript
import { vi } from 'vitest';
import { server } from './test/mocks/server';
import { http, HttpResponse } from 'msw';

// Mock SSE endpoint
server.use(
  http.post('/v1/responses', () => {
    return HttpResponse.json({ ... });
  })
);
```

---

## Common Tasks

### Adding a New Component

1. Create component file: `src/components/my-component.tsx`
2. Define TypeScript interface for props
3. Use Tailwind for styling
4. Export from component file
5. Add tests: `src/test/my-component.test.tsx`

```typescript
// my-component.tsx
interface MyComponentProps {
  title: string;
  onAction: () => void;
}

export function MyComponent({ title, onAction }: MyComponentProps) {
  return (
    <div className="p-4">
      <h2 className="text-lg font-bold">{title}</h2>
      <button onClick={onAction}>Action</button>
    </div>
  );
}
```

### Adding a shadcn/ui Component

```bash
# From frontend directory
npx shadcn@latest add <component>

# Example: Add dialog
npx shadcn@latest add dialog

# Use in code
import { Dialog, DialogContent, DialogHeader } from '@/components/ui/dialog';
```

### Handling Approval Flow

When `approval_required` event arrives:

```typescript
const [approvalRequest, setApprovalRequest] = useState(null);

// In useFastAPIChat hook or component
if (event.type === "approval_required") {
  setApprovalRequest(event);
  // Show approval modal
}

// On user decision
async function handleApprovalDecision(
  decision: "approve" | "reject" | "modify"
) {
  await fetch("/v1/approval/response", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request_id: approvalRequest.request_id,
      decision,
      modified_code: modifiedCode, // if decision === 'modify'
    }),
  });
  setApprovalRequest(null);
}
```

### Adding New Route/Page

1. Create route component in `src/app/`
2. Add route to router (if using React Router)
3. Update navigation

---

## Performance Optimization

### Lazy Loading

```typescript
import { lazy, Suspense } from "react";

const HeavyComponent = lazy(() => import("./heavy-component"));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <HeavyComponent />
    </Suspense>
  );
}
```

### Memoization

```typescript
import { useMemo, useCallback } from "react";

function ExpensiveComponent({ data }) {
  const processedData = useMemo(() => {
    return data.map(/* expensive operation */);
  }, [data]);

  const handleClick = useCallback(() => {
    // Event handler
  }, [dependencies]);
}
```

### Preventing Rerenders

```typescript
import { memo } from "react";

export const Message = memo(function Message({ content, role }) {
  return <div>{content}</div>;
});
```

---

## Debugging

### React DevTools

Install React DevTools browser extension:

- View component tree
- Inspect props and state
- Profile performance

### Console Logging

```typescript
// Development only
if (import.meta.env.DEV) {
  console.log("Debug:", { messages, isStreaming });
}
```

### Network Tab

- Monitor SSE connections (`/v1/responses`)
- Check request/response payloads
- Verify proxy configuration

### Error Boundaries

```typescript
import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

class ErrorBoundary extends Component<Props, State> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return <div>Something went wrong</div>;
    }
    return this.props.children;
  }
}
```

---

## Build and Deployment

### Production Build

```bash
# Build for production
npm run build

# Output: dist/
# - Minified JavaScript
# - Optimized CSS
# - Source maps (if enabled)
```

### Environment Variables

Vite exposes env vars prefixed with `VITE_`:

```bash
# .env
VITE_API_URL=https://api.example.com
```

```typescript
// Access in code
const apiUrl = import.meta.env.VITE_API_URL;
```

### Preview Build

```bash
# Preview production build locally
npm run preview
```

---

## Common Pitfalls

### ❌ Rewriting SSE Hook

Never reimplement `useFastAPIChat`. It handles:

- SSE connection lifecycle
- Event parsing
- Content buffering
- Error handling
- Reconnection logic

**Use the hook as-is.**

### ❌ Inline Styles

Avoid inline styles. Use Tailwind utility classes:

```tsx
// ❌ WRONG
<div style={{ padding: '1rem', backgroundColor: '#f3f4f6' }}>

// ✅ CORRECT
<div className="p-4 bg-gray-100">
```

### ❌ Missing Type Annotations

Always type function parameters and return values:

```typescript
// ❌ WRONG
function process(data) {
  return data.map((x) => x * 2);
}

// ✅ CORRECT
function process(data: number[]): number[] {
  return data.map((x) => x * 2);
}
```

### ❌ Direct DOM Manipulation

Use React state instead of direct DOM manipulation:

```typescript
// ❌ WRONG
document.getElementById("message").textContent = "Hello";

// ✅ CORRECT
const [message, setMessage] = useState("");
setMessage("Hello");
```

### ❌ Not Using Proxy

All API calls should go through Vite proxy. Don't hardcode backend URLs:

```typescript
// ❌ WRONG
fetch("http://localhost:8000/v1/responses");

// ✅ CORRECT
fetch("/v1/responses"); // Proxied automatically
```

---

## Code Quality

### Before Committing

```bash
# Lint
npm run lint

# Type check
npx tsc --noEmit

# Test
npm run test

# Build (ensures no build errors)
npm run build
```

### ESLint Configuration

Follows React and TypeScript best practices:

- No unused variables
- Proper React hooks usage
- TypeScript strict mode

---

## References

- **Root AGENTS.md**: `../../AGENTS.md` (general project instructions)
- **Vite Documentation**: https://vite.dev/
- **React Documentation**: https://react.dev/
- **shadcn/ui**: https://ui.shadcn.com/
- **Tailwind CSS**: https://tailwindcss.com/
- **Vitest**: https://vitest.dev/
- **TypeScript**: https://www.typescriptlang.org/

---

## Quick Command Reference

```bash
# Development
npm run dev              # Start dev server (port 5173)
npm run build            # Build for production
npm run preview          # Preview production build

# Quality
npm run lint             # Lint code
npm run test             # Run tests
npx tsc --noEmit         # Type check

# shadcn/ui
npx shadcn@latest add <component>  # Add UI component

# Package management
npm install              # Install dependencies
npm install <package>    # Add new package
npm update               # Update packages
```

---

## Frontend-Specific Notes

- Frontend uses **npm**, backend uses **uv**—don't mix package managers
- All API routes automatically proxied through Vite dev server
- SSE streaming is core to the UI—never bypass `useFastAPIChat` hook
- Use shadcn/ui components for consistency—don't create custom UI primitives
- Tailwind CSS is the only styling approach—no CSS modules or styled-components
- TypeScript strict mode is enabled—all code must be fully typed
- Tests use Vitest (not Jest)—syntax is similar but not identical
- HMR is instant—save file to see changes immediately
