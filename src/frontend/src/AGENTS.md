# AGENTS.md – Frontend (React / Vite / TypeScript)

> Agent-focused guide for working inside `src/frontend/`. Complements root `AGENTS.md`. Optimized for autonomous & semi-autonomous coding agents.

---

## Quick Start

**Essential frontend commands:**

```bash
# From repository root:
make frontend-install  # Install dependencies
make frontend-dev      # Start dev server (port 5173)

# From src/frontend/src/:
npm install      # Install dependencies
npm run dev      # Start dev server
npm run build    # Production build
npm run lint     # Check code
npm run lint:fix # Auto-fix issues

# Test integration with backend:
# Terminal 1: make dev        (full stack)
# OR Terminal 1: make backend (API only)
# Terminal 2: npm run dev     (if backend already running)
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
| Bundler    | Vite                                          | Fast TS HMR, env via `import.meta.env`            |
| Framework  | React 18                                      | Functional components + hooks only                |
| Language   | TypeScript                                    | Strict; avoid `any` unless isolated adapter layer |
| UI Library | shadcn/ui + Radix Primitives                  | Accessible component primitives                   |
| Styling    | Tailwind CSS + utility patterns               | Prefer composition over custom CSS                |
| State      | Local + lightweight stores (`zustand`)        | Keep ephemeral vs persistent separate             |
| Data / IO  | Fetch + React Query (`@tanstack/react-query`) | SSE stream manually handled                       |
| Markdown   | `react-markdown` + `shiki`                    | Syntax highlighting for streamed code             |
| Charts     | Recharts                                      | Used in analyst outputs                           |

---

## 3. Directory Layout (High Signal)

```
src/frontend/src
├── App.tsx / main.tsx          # Application shell + bootstrap
├── api/                        # REST helpers (e.g., chatApi.ts)
├── components/
│   ├── ai/                     # Plan, reasoning, stream visualisations
│   ├── features/               # UI composites (chat, approval, shared)
│   └── ui/
│       ├── shadcn/             # Generated primitives (managed via CLI)
│       └── custom/             # App-specific UI atoms/molecules
├── features/
│   └── chat/                   # Domain hooks (useChatController, useChatClient)
├── hooks/                      # Cross-cutting hooks (approval, history, SSE)
├── lib/                        # API config, TanStack Query wrappers, use-fastapi-chat orchestrator, utilities
├── pages/                      # Route-level components (ChatPage, fallback)
├── stores/                     # Zustand stores (chatStore, approvalStore, conversationStore)
├── utils/                      # Formatting helpers, constants
├── test/                       # Vitest setup/helpers
├── tests/                      # Test files organized by source structure
│   ├── lib/                    # Tests for lib/ modules
│   ├── hooks/                  # Tests for hooks/ modules
│   ├── components/features/     # Tests for components/features/ modules
│   └── features/               # Tests for features/ modules
├── public/                     # Static assets served by Vite
├── dist/                       # Generated build output (ignored in git)
├── index.html                  # Vite entry
├── vite.config.ts              # Build + alias config (`@` → `src/`)
├── tailwind.config.ts          # Tailwind + shadcn integration
└── components.json             # shadcn component registry

**Import conventions:**
- Feature composites: `import { ChatContainer } from '@/components/features/chat'`
- Domain hooks: `import { useChatController } from '@/features/chat'`
- AI widgets: `import { Plan } from '@/components/ai'`
- shadcn primitives: `import { Button } from '@/components/ui/shadcn/button'` (no barrel)
- Custom UI atoms: `import { Message } from '@/components/ui/custom/message'`

**Ownership notes:**
- `components/features/*` — UI surfaces bound to business logic (safe to iterate).
- `features/*` — Hook orchestration and domain logic; update alongside corresponding stores.
- `components/ui/shadcn/*` — Generated; modify via `npx shadcn-ui` workflows only.
- `stores/` — Centralised Zustand stores. Keep selectors memoized and state minimal.
- `lib/` — Shared orchestrators (`use-fastapi-chat`), API config, TanStack query helpers; treat as single source of truth for network requests.
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
cd src/frontend/src && npm install

# Dev server (5173 or 8080 depending on config)
cd src/frontend/src && npm run dev

# Production build
cd src/frontend/src && npm run build

# Development (unminified) build
cd src/frontend/src && npm run build:dev

# Preview build output
cd src/frontend/src && npm run preview

# Lint / format
cd src/frontend/src && npm run lint
cd src/frontend/src && npm run lint:fix
cd src/frontend/src && npm run format
```

---

## 6. Streaming & Event Model

The backend emits OpenAI **Responses API**-compatible SSE messages plus a few Fleet-specific helpers. Events you must handle:

| Event Type             | Purpose                                             | UI Action                                                      |
| ---------------------- | --------------------------------------------------- | -------------------------------------------------------------- |
| `response.delta`       | Streaming token/segment from a specialist agent     | Append to active streaming message; attribute by `agent_id`.   |
| `orchestrator.message` | Manager narration (plan ledger, progress notes)     | Render in sidebar / timeline (`Plan`, `Progress` panes).       |
| `progress`             | Synthetic helper emitted when agents start/complete | Update status indicators (`planning`, `agent.starting`, etc.). |
| `response.completed`   | Final assistant message with aggregated content     | Finalize message, unlock composer, persist to history.         |
| `error`                | Execution failure                                   | Surface toast + mark conversation errored; stop streaming.     |

The stream always terminates with `data: [DONE]`. Parser MUST remain tolerant of additional keys (log + ignore). When adding new event types:

1. Extend discriminated union in `lib/use-fastapi-chat.ts` and `hooks/useMessageState.ts`.
2. Update reducers/stores as needed.
3. Add Vitest coverage for regression (`tests/hooks/useMessageState.test.ts`, `tests/lib/use-fastapi-chat.test.ts`).

---

## 7. HITL approval flow (frontend perspective)

1. Listen for `response.function_approval.requested` (new Responses format) or legacy `approval_request`.
2. Extract `{ request_id, request }` and push into the Zustand approval queue via `useApprovalWorkflow.handleApprovalRequested`.
3. Render modal (`components/features/approval/ApprovalPrompt.tsx`) with the provided context.
4. User selects Approve / Reject / Modify; disable actions while `respondToApproval` posts to `/v1/approvals/{request_id}`.
5. The backend replies with `response.function_approval.responded`; remove the request through `handleApprovalResponded`.
6. Surface transport errors and allow retry—never silently drop responses.

```json
{
  "decision": "approve|reject|modify",
  "modified_details": {
    "code": "... optional ..."
  },
  "reason": "optional reviewer note"
}
```

The approval store (`src/frontend/src/stores/approvalStore.ts`) already tracks optimistic states; keep selectors memoized so modals update efficiently.

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

## 13. Testing strategy (frontend)

- Test files are organized in `tests/` directory, mirroring the source directory structure:
  - `tests/lib/` — Tests for `lib/` modules (e.g., `use-fastapi-chat.test.ts`)
  - `tests/hooks/` — Tests for `hooks/` modules (e.g., `useApprovalWorkflow.test.ts`, `useMessageState.test.ts`)
  - `tests/components/features/` — Tests for `components/features/` modules (e.g., `chat/ChatContainer.test.tsx`, `approval/ApprovalPrompt.test.tsx`)
  - `tests/features/` — Tests for `features/` modules (e.g., `chat/useChatClient.test.ts`)
- All test files use the `@/` alias for imports (e.g., `import { useFastAPIChat } from "@/lib/use-fastapi-chat"`).
- Run `npm run test` or `npm run test -- --watch` from `src/frontend/src`. Use `npm run test:ui` for focused debugging and `npm run test:coverage` to surface regressions.
- When simulating SSE, stub the event stream via the utilities in `test/sseTestUtils.ts` (or extend if additional helpers are required).
- Full-stack Playwright coverage resides in the Python suite (`tests/test_backend_e2e.py`). Execute it via `make test-e2e` once the dev stack is running.

---

## 14. Adding a New Workflow Mode (Frontend)

1. Extend mode enum / store.
2. Add selection control (dropdown / segmented switch).
3. Adjust SSE request payload (model / workflow identifier).
4. Gracefully handle mode-specific events (feature-detect).
5. Update root `AGENTS.md` + this file if contract changes.

---

## 15. API Integration Rules

- Centralize fetch logic: use `lib/api-config.ts` for endpoints/URLs and the helpers in `api/chatApi.ts` (or extend that module).
- POST payloads **must** include `Content-Type: application/json`; use `fetchWithRetry` in `lib/use-fastapi-chat.ts` for resilient submissions.
- Abort stale requests when switching models or resetting conversations (call `AbortController` via `use-fastapi-chat` utilities).
- SSE uses `fetch + ReadableStream`; reconnection remains manual—do not auto-retry while approvals are pending.
- When introducing new endpoints, add matching TanStack Query entries in `lib/queries/` and document fallback behaviour.

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

| Action                  | Check Before Proceeding                                                          |
| ----------------------- | -------------------------------------------------------------------------------- |
| Modifying SSE parser    | Confirm backend event schema unchanged (search for `response.function_approval`) |
| Adding dependency       | Ensure not duplicating existing functionality; update lock + docs                |
| Editing Tailwind config | Verify no class name collisions / remove dead tokens                             |
| Changing build config   | Run `npm run build` and manual smoke (open `dist/`)                              |

---

## 19. Quick Command Reference

```bash
# Install & run
make frontend-install
cd src/frontend/src && npm run dev

# Lint & format
cd src/frontend/src && npm run lint
cd src/frontend/src && npm run lint:fix
cd src/frontend/src && npm run format

# Build / preview
cd src/frontend/src && npm run build
cd src/frontend/src && npm run preview
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
