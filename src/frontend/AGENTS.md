# AGENTS.md – Frontend (React / Vite / TypeScript)

> Agent-focused guide for working inside `src/frontend/`. Complements root `AGENTS.md`. Optimized for autonomous & semi-autonomous coding agents.

---

## Quick Start

**Essential frontend commands:**

```bash
# From repository root:
make frontend-install  # Install dependencies
make frontend-dev      # Start dev server (port 5173)

# From src/frontend/:
npm install      # Install dependencies
npm run dev      # Start dev server
npm run build    # Production build
npm run lint     # Check code
npm run lint:fix # Auto-fix issues

# Test integration with backend:
# Terminal 1: uv run agentic-fleet (full stack)
# OR Terminal 1: make haxui-server (backend only)
# Terminal 2: npm run dev (if not using agentic-fleet)
```

---

## 1. Purpose & Scope

The frontend provides a **real-time multi-agent interaction UI** with:

- SSE streaming of Responses API events (OpenAI-compatible)
- HITL (Human-in-the-Loop) approval dialogs
- Workflow model selection (Fleet / Reflection / Dynamic)
- Multi-pane code + analysis + chat surfaces

This file documents how an agent should safely modify, extend, and validate the frontend without breaking backend contracts.

---

## 2. Tech Stack Summary

| Area       | Choice                                        | Notes                                             |
| ---------- | --------------------------------------------- | ------------------------------------------------- |
| Bundler    | Vite 7.1.12                                   | Fast TS HMR, env via `import.meta.env`            |
| Framework  | React 18                                      | Functional components + hooks only                |
| Language   | TypeScript                                    | Strict; avoid `any` unless isolated adapter layer |
| UI Library | shadcn/ui + Radix Primitives                  | Accessible component primitives                   |
| Styling    | Tailwind CSS + utility patterns               | Prefer composition over custom CSS                |
| Animations | Framer Motion 12.23.24                        | Layout and component animations                   |
| State      | Local + lightweight stores (`zustand`)        | Keep ephemeral vs persistent separate             |
| Data / IO  | Fetch + React Query (`@tanstack/react-query`) | SSE stream manually handled                       |
| Markdown   | `react-markdown` + `shiki`                    | Syntax highlighting for streamed code             |
| Charts     | Recharts                                      | Used in analyst outputs                           |

---

## 3. Directory Layout (High Signal)

```text
src/frontend/
├── src/
│   ├── components/
│   │   ├── features/           # Feature-specific components (business logic)
│   │   │   ├── chat/          # Chat feature: ChatContainer, ChatMessage, ChatInput, ChatHeader, ChatSidebar
│   │   │   ├── approval/      # HITL approval: ApprovalPrompt
│   │   │   └── shared/        # Shared features: ErrorBoundary, ConnectionStatusIndicator
│   │   ├── ai/                # AI visualization components (plans, reasoning, tools, steps, streaming)
│   │   └── ui/
│   │       ├── shadcn/        # shadcn/ui primitives (DON'T MODIFY - managed by CLI)
│   │       └── custom/        # App-specific UI components (safe to modify)
│   ├── layouts/               # Layout components with framer-motion animations
│   │   ├── MainLayout.tsx     # Main application layout wrapper
│   │   ├── ChatLayout.tsx     # Chat-specific layout with sidebar/header
│   │   └── index.ts           # Layout barrel exports
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Helper utilities and API clients
│   │   ├── hooks/            # Specialized hooks
│   │   │   ├── useMessageState.ts      # Message accumulation & streaming
│   │   │   ├── useApprovalWorkflow.ts  # HITL approval management
│   │   │   ├── useConversationHistory.ts # Conversation loading
│   │   │   └── useSSEConnection.ts      # SSE event types
│   │   ├── types/            # Type definitions
│   │   │   └── contracts.ts  # Backend contract types
│   │   ├── agent-utils.ts    # Agent role/color mapping
│   │   ├── api-config.ts     # API endpoints & URL builder
│   │   ├── types.ts          # Core frontend types
│   │   ├── utils.ts          # Utility functions
│   │   └── use-fastapi-chat.ts # Main chat orchestration hook
│   ├── pages/                 # Router-level pages (Index, NotFound)
│   └── app/                   # App state (chat-store, API primitives)
├── index.html                 # Vite entry
├── vite.config.ts             # Build + alias config (@/ alias → src/)
├── tailwind.config.ts         # Tailwind + shadcn integration
└── components.json            # shadcn component registry

**Import Conventions:**
- Features: `import { ChatContainer } from '@/components/features/chat'` (barrel exports)
- AI: `import { Plan, Reasoning } from '@/components/ai'` (barrel exports)
- Layouts: `import { MainLayout, ChatLayout } from '@/layouts'` (barrel exports)
- shadcn: `import { Button } from '@/components/ui/shadcn/button'` (individual imports, no barrel)
- Custom UI: `import { Message } from '@/components/ui/custom/message'` (individual imports)
- Lib: `import { mapRoleToAgent } from '@/lib/agent-utils'` (individual imports)

**Component Ownership:**
- `features/` - Safe to modify, application business logic
- `ai/` - Safe to modify, AI-specific visualization
- `layouts/` - Safe to modify, uses framer-motion for animations
- `ui/shadcn/` - DO NOT MODIFY, use shadcn CLI for updates
- `ui/custom/` - Safe to modify, app-specific UI building blocks
- `lib/` - Safe to modify, utility functions and API clients
```

---

## 4. Environment & Configuration

Runtime env values are injected via Vite (`import.meta.env`). Avoid hardcoding backend URLs.

| Variable             | Typical Value           | Purpose               |
| -------------------- | ----------------------- | --------------------- |
| `VITE_BACKEND_URL`   | `http://localhost:8000` | API / SSE base URL    |
| `VITE_DEFAULT_MODEL` | `fleet`                 | Initial workflow mode |

If adding new env keys:

1. Add to `.env.local` (never commit secrets)
2. Prefix with `VITE_`
3. Reference using `import.meta.env.VITE_<NAME>`
4. Update documentation + fallback logic

---

## 5. Commands

```bash
# Install deps (from repo root)
make frontend-install
# or manually
cd src/frontend && npm install

# Dev server (5173 or 8080 depending on config)
npm run dev

# Production build
npm run build

# Development (unminified) build
npm run build:dev

# Preview build output
npm run preview

# Lint / format
npm run lint
npm run lint:fix
npm run format
```

---

## 6. Streaming & Event Model

The backend emits OpenAI **Responses API** style SSE events. Common types consumed:

| Event Type                  | Purpose                  | Action in UI                    |
| --------------------------- | ------------------------ | ------------------------------- |
| `content_block_delta`       | Partial token text       | Append to active message buffer |
| `response_output_item_done` | Message segment complete | Seal current block              |
| `approval_required`         | HITL operation pending   | Trigger approval modal & queue  |
| `tool_call_delta`           | Tool streaming output    | Render tool scratch panel       |
| `response_completed`        | Workflow finished        | Unlock input / flush state      |

Parser MUST be resilient to unknown event types (log + ignore). When modifying event handling:

- Keep backward compatibility (feature-detect new types)
- Do not block UI on unknown payloads

---

## 7. HITL Approval Flow (Frontend Perspective)

1. Receive `approval_required` event with `request_id`, `operation_type`, `details`.
2. Store in approval queue store (`zustand`).
3. Present modal (include operation preview — e.g. code snippet, dataset summary).
4. User picks APPROVE / REJECT / MODIFY.
5. POST decision to backend endpoint (ensure proper JSON schema):

```json
{
  "request_id": "...",
  "decision": "approve|reject|modify",
  "modified_data": { "code": "<optional>" }
}
```

6. Disable buttons while awaiting 200 OK.
7. Optimistically reflect decision (with rollback on failure).

Never silently drop approval responses. Log transport errors with user hint.

---

## 8. State Management Guidance

| Category          | Strategy                     | Notes                                   |
| ----------------- | ---------------------------- | --------------------------------------- |
| Streaming buffer  | Local component state        | Reset per session/task                  |
| Workflow metadata | Zustand store                | Mode, active agent, task status         |
| Approvals         | Dedicated zustand slice      | Queue semantics FIFO                    |
| Caching (history) | React Query / ephemeral list | Persist only if backend supports replay |

Avoid global stores for transient UI-only toggles (favor local state + props).

---

## 9. Type Safety Patterns

- Mirror backend event types in a single `types/events.ts` (union discriminant: `type`).
- Use exhaustive `switch(event.type)` + `never` fallback to catch unhandled cases.
- No `any`; if shape unknown, narrow safely: `if ('operation_type' in ev)`.
- Export stable prop interfaces for complex components.

---

## 10. Adding UI Components

Checklist:

1. Co-locate in `components/` (or domain folder if specialized).
2. Provide semantic, accessible markup (label associations, roles).
3. Avoid coupling to fetch layer; accept injected callbacks.
4. Export from an `index.ts` barrel if reused widely.
5. Add story / usage example (placeholder: optional future Storybook integration).

---

## 11. Theming & Styling

- Prefer Tailwind utility classes; avoid deep CSS overrides.
- Use `cn()` helper or `clsx` + `tailwind-merge` to compose dynamic class sets.
- For new design tokens, extend `tailwind.config.ts` (do **not** inline repeated arbitrary values).

---

## 12. Performance Considerations

| Area                 | Concern                 | Mitigation                                         |
| -------------------- | ----------------------- | -------------------------------------------------- |
| Streaming re-renders | Character-level updates | Batch with `requestAnimationFrame` or chunk commit |
| Large message lists  | Scroll jank             | Virtualize if >200 rendered nodes (future)         |
| Syntax highlighting  | Blocking on large code  | Use async `shiki` + fallback skeleton              |
| Approval modals      | State churn             | Isolate modal subtree via portal                   |

---

## 13. Testing Strategy (Frontend)

(Current repo emphasizes backend pytest; frontend test infra may be minimal.) If adding tests:

- Use Playwright for E2E (already present under `tests/e2e/`).
- Keep potential future unit tests colocated: `*.test.tsx` (Vitest / Jest if introduced).
- Mock SSE layer with an event emitter abstraction.

---

## 14. Adding a New Workflow Mode (Frontend)

1. Extend mode enum / store.
2. Add selection control (dropdown / segmented switch).
3. Adjust SSE request payload (model / workflow identifier).
4. Gracefully handle mode-specific events (feature-detect).
5. Update root `AGENTS.md` + this file if contract changes.

---

## 15. API Integration Rules

- Centralize fetch logic (e.g., `lib/api.ts`).
- Always include `Content-Type: application/json` for POST.
- Abort stale requests on model switch / session reset.
- SSE: Use native `EventSource` or `fetch + ReadableStream` poly (depending on backend). Ensure reconnection strategy is **manual** (do not auto-reconnect mid-approval).

---

## 16. Error Handling UX

| Scenario                | UI Behavior                 |
| ----------------------- | --------------------------- |
| SSE connection lost     | Banner + retry affordance   |
| Backend 500             | Toast w/ truncated error id |
| Approval submit failure | Modal inline error + retry  |
| Unknown event type      | Console warn only           |

Never expose raw stack traces to end user UI.

---

## 17. Accessibility & UX Notes

- Provide `aria-live="polite"` region for streaming text.
- Ensure focus trap in approval modals.
- Keyboard shortcuts (future): plan layering; avoid stealing browser defaults.

---

## 18. Safe Automation Guardrails (For Agents)

| Action                  | Check Before Proceeding                                                 |
| ----------------------- | ----------------------------------------------------------------------- |
| Modifying SSE parser    | Confirm backend event schema unchanged (search for `approval_required`) |
| Adding dependency       | Ensure not duplicating existing functionality; update lock + docs       |
| Editing Tailwind config | Verify no class name collisions / remove dead tokens                    |
| Changing build config   | Run `npm run build` and manual smoke (open `dist/`)                     |

---

## 19. Quick Command Reference

```bash
# Install & run
make frontend-install && npm run dev

# Lint & format
npm run lint && npm run lint:fix && npm run format

# Build / preview
npm run build && npm run preview
```

---

## 20. Update Procedure

When changing frontend-backend contract:

1. Update TS types
2. Adjust parser + UI mapping
3. Run backend focused tests (make test)
4. Smoke test streaming & approval manually
5. Update root + related AGENTS docs

---

**End – Frontend AGENTS.md**
