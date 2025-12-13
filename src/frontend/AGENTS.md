# Frontend AGENTS.md

## Overview

The frontend lives in `src/frontend/src/` and is built with Vite + React 19 + TypeScript + Tailwind
CSS v4. It renders the AgenticFleet chat UI, consumes backend REST endpoints under `/api/v1`, and
streams workflow events over WebSocket (`/api/ws/chat`).

## Tooling

- Package manager: `npm` (see root `Makefile` targets).
- Animations: `motion/react` (do not add `framer-motion`).
- Styling: Tailwind v4 + tokenized CSS under `src/styles/`.

## Directory Map

| Path                            | Purpose                                                               |
| ------------------------------- | --------------------------------------------------------------------- |
| `src/main.tsx`                  | Bootstrap (providers + mount).                                        |
| `src/App.tsx`                   | App shell and initial load.                                           |
| `src/components/blocks/`        | Prompt-kit blocks (e.g. `full-chat-app`).                             |
| `src/components/ui/`            | Shared primitives (Radix/shadcn-style wrappers).                      |
| `src/components/prompt-kit/`    | Prompt-kit UI building blocks (markdown, reasoning, steps, input).    |
| `src/api/`                      | Typed API layer (HTTP wrapper, clients, hooks, WebSocket service).    |
| `src/stores/`                   | Zustand stores (chat state + stream event handling).                  |
| `src/lib/`                      | Shared helpers (markdown/code detection, utils).                      |
| `src/styles/` + `src/index.css` | Design tokens + Tailwind v4 theme + app utilities (e.g. `glass-bar`). |
| `src/test/`, `src/tests/`       | Vitest setup + unit tests.                                            |

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
- WebSocket streaming: `src/api/websocket.ts` (connects to `/api/ws/chat`).
- Chat state: `src/stores/chatStore.ts`:
  - creates/selects conversations
  - sends chat requests over WS
  - normalizes stream events into message `steps` for the UI

## UI Guidelines

- Keep pages thin (validate/select state + compose components).
- Prefer Prompt-kit blocks under `src/components/blocks/` and reusable atoms under `src/components/ui/*`.
- When adding new streaming event kinds, update:
  - `src/api/types.ts` (types)
  - `src/stores/chatStore.ts` (event handling/mapping)
  - tests under `src/tests/` as appropriate
