# AGENTS.md

## Overview

The frontend lives in `src/frontend/src/` and is built with Vite + React + TypeScript. It renders the
Agentic Fleet chat surface, consumes the backend Responses SSE stream, and visualises agent-specific
progress (chain of thought, reasoning, and orchestrator messages). This document covers structure,
state management, and development workflow for the SPA.

## Directory Map

| Path                  | Purpose                                                                                                                                                                           |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `App.tsx`, `main.tsx` | Application shell that injects routing/context and mounts the chat page.                                                                                                          |
| `pages/ChatPage.tsx`  | Top-level layout for the chat experience; wires stores, components, and prompts.                                                                                                  |
| `components/`         | Feature components. `components/chat/` renders message streams, `components/prompt-kit/` houses prompt helpers, `components/ui/` wraps shadcn/ui primitives plus custom UI atoms. |
| `stores/chatStore.ts` | Zustand store managing conversation state, SSE deltas, orchestrator messages, and errors.                                                                                         |
| `lib/api/`            | REST + SSE clients (`chat.ts`, `magentic-workflow.ts`). All backend calls flow through here.                                                                                      |
| `lib/parsers/`        | Helpers that translate Responses payloads into frontend-friendly shapes.                                                                                                          |
| `lib/config.ts`       | Resolves `API_BASE_URL` from environment variables (`VITE_API_BASE_URL`).                                                                                                         |
| `hooks/`              | Future custom hooks live here. (Empty by default to keep structure consistent with backend docs.)                                                                                 |
| `types/`              | Shared TypeScript types for chat payloads, workflow entities, and SSE event envelopes.                                                                                            |
| `assets/`             | Images or static resources consumed by the SPA.                                                                                                                                   |
| `test/`               | Vitest setup utilities (msw handlers, test utils).                                                                                                                                |

## Development Workflow

- Install dependencies from the repo root: `make frontend-install` (runs `npm install` inside
  `src/frontend/src`). Use `make dev-setup` to bundle backend + frontend prerequisites.
- Local dev: `make dev` to launch backend + frontend together, or `make frontend-dev` to run only the
  SPA on <http://localhost:5173>.
- Production build: `make build-frontend` (internally calls `npm run build` and copies assets into
  `src/agentic_fleet/ui`).
- Environment configuration lives in `.env` (root) or `.env.local` (frontend). Set `VITE_API_BASE_URL`
  to point at the backend (`http://localhost:8000` by default).
- When adjusting bundler or lint settings, update `vite.config.ts`, `tsconfig.json`, and
  `package.json` scripts together.

## State & Data Flow

- The SPA creates conversations via `lib/api/chat.createConversation()` and streams responses through
  `lib/api/chat.streamChatResponse()`, which implements an SSE reader that emits deltas,
  orchestrator updates, and agent completion events.
- `stores/chatStore.ts` (Zustand) is the single source of truth for messages, streaming deltas, and
  orchestration metadata. Always go through store actions (`sendMessage`, `reset`, etc.) rather than
  mutating React state directly.
- Types under `types/chat.ts` define the shared payload structures. Keep them in sync with backend
  Pydantic models located in `src/agentic_fleet/models/`.
- Parsers in `lib/parsers/` translate raw Responses events into the UI-friendly format (chain of
  thought display, reasoning breakdown, etc.). Update these alongside backend event schema changes.

## UI Patterns

- Components in `components/chat/` render agent messages, chain-of-thought reveals, structured content
  blocks, and reasoned steps. They are designed to be dumb—business logic stays in the store or `lib/`.
- `components/ui/` hosts re-exported shadcn/ui primitives plus bespoke atoms (prompt input, streaming
  indicator, markdown renderer, tool badges). Prefer composing these atoms rather than creating ad-hoc
  styling in pages.
- `components/prompt-kit/` holds prompt suggestions and saved prompt utilities; keep data-driven
  content here for reuse across surfaces.
- CSS lives in `App.css`, `index.css`, and component-level styles (mostly Tailwind utility classes).
  Update `src/frontend/src/assets` when introducing new images or icons.

## Testing & Quality

- Unit and component tests: run `npm run test` (Vitest). Specs live alongside components (`*.test.tsx`)
  or in dedicated `__tests__` folders (e.g. `stores/__tests__/chatStore.test.ts`).
- Linting & formatting: `npm run lint` executes ESLint with the same config as CI; Prettier runs via
  IDE integration. Keep formatting-only changes separate from logic updates.
- End-to-end flows: `make test-e2e` (Playwright) requires both backend and frontend running via
  `make dev`. Update fixtures in `tests/e2e/` when UI behaviours change.
- Snapshot updates or large UI changes should include screenshots in the PR description per the root
  documentation guidelines.

## Update Checklist

- Backend API, workflow, or SSE schema changes must update `lib/api/`, `lib/parsers/`, relevant store
  actions, and the documentation chain (`src/agentic_fleet/AGENTS.md`, `tests/AGENTS.md`).
- Adding visual features? Extend `components/ui/` or `components/chat/` and update the accessibility
  affordances (focus states, aria labels).
- Introducing new global state? Add a typed store or hook—avoid prop drilling through `ChatPage`.
- After touching docs or store logic, run `make validate-agents`, `npm run lint`, and `npm run test`
  before committing.
