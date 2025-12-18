# Frontend AGENTS.md

## Overview

The frontend lives in `src/frontend/src/` and is built with Vite + React 19 + TypeScript + Tailwind
CSS v4. It renders the AgenticFleet chat UI, consumes backend REST endpoints under `/api/v1`, and
streams workflow events primarily over **SSE** (`/api/chat/:conversation_id/stream`). A WebSocket
client exists for experimentation/backward-compat, but the current chat uses SSE.

## Tooling

- Package manager: `npm` (see root `Makefile` targets).
- Animations: `motion/react` (do not add `framer-motion`).
- Styling: Tailwind v4 + tokenized CSS under `src/styles/` + `src/index.css`.

## Directory Map

| Path                            | Purpose                                                               |
| ------------------------------- | --------------------------------------------------------------------- |
| `src/main.tsx`                  | Bootstrap (providers + mount).                                        |
| `src/App.tsx`                   | App shell and initial load.                                           |
| `src/components/ui/`            | Shared primitives (Radix/shadcn-style wrappers).                      |
| `src/features/chat/`            | Chat feature (UI + store + streaming UI components).                  |
| `src/features/dashboard/`       | Optimization dashboard (DSPy tooling UI).                             |
| `src/api/`                      | Typed API layer (HTTP wrapper, clients, hooks, SSE client).           |
| `src/lib/`                      | Shared helpers (markdown/code detection, utils).                      |
| `src/hooks/`                    | Shared hooks (e.g. responsive helpers).                               |
| `src/contexts/`                 | React contexts/providers (theme, etc.).                               |
| `src/styles/` + `src/index.css` | Design tokens + Tailwind v4 theme + app utilities (e.g. `glass-bar`). |
| `src/tests/`                    | Vitest setup + unit tests.                                            |

## Development Workflow

# from repo root

- Install deps: `make frontend-install`
- Run frontend: `make frontend-dev` (http://localhost:5173)
- Run full stack: `make dev` (backend + frontend)
- Lint: `make frontend-lint`
- Tests: `make test-frontend`
- Build: `make build-frontend`

## State & Data Flow

- REST: `src/api/http.ts` + `src/api/client.ts` (prefix `/api/v1`).
- SSE streaming: `src/api/sse.ts` (connects to `/api/chat/:id/stream`).
- Chat state: `src/features/chat/stores/chatStore.ts`:
  - creates/selects conversations
  - sends chat requests over SSE
  - normalizes stream events into message `steps` for the UI
  - persists UI preferences (trace visibility, raw reasoning toggle)

## UI Guidelines

- Keep pages thin (validate/select state + compose components).
- Prefer feature UI under `src/features/*` and reusable atoms under `src/components/ui/*`.
- When adding new streaming event kinds, update:
  - `src/api/types.ts` (types)
  - `src/features/chat/stores/chatStore.ts` (event handling/mapping)
  - tests under `src/tests/` as appropriate
