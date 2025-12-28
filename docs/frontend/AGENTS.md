# Frontend AGENTS.md

## Overview

The frontend lives in `src/frontend/src/` and is built with Vite + React 19 + TypeScript + Tailwind
CSS v4. It renders the AgenticFleet chat UI, consumes backend REST endpoints under `/api/v1`, and
streams workflow events primarily over **SSE** (`/api/chat/:conversation_id/stream`). A WebSocket
client exists for experimentation/backward-compat, but the current chat uses SSE.

## Backend Architecture Context (v0.7.0)

The frontend connects to a **FastAPI backend** with a layered architecture:

```
Frontend (React) ←→ API Layer ←→ Services Layer ←→ Workflows ←→ DSPy/Agents
```

- **SSE Streaming**: `services/chat_sse.py` handles Server-Sent Events
- **WebSocket**: `services/chat_websocket.py` handles real-time bidirectional communication
- **Event Mapping**: `api/v1/events/mapping.py` transforms workflow events to UI-friendly payloads

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

```bash
# from repo root
make frontend-install  # Install deps
make frontend-dev      # Run frontend (http://localhost:5173)
make dev               # Run full stack (backend + frontend)
make frontend-lint     # Lint
make test-frontend     # Tests
make build-frontend    # Build
```

## State & Data Flow

- REST: `src/api/http.ts` + `src/api/client.ts` (prefix `/api/v1`).
- SSE streaming: `src/api/sse.ts` (connects to `/api/chat/:id/stream`).
- Chat state: `src/features/chat/stores/chatStore.ts`:
  - creates/selects conversations
  - sends chat requests over SSE
  - normalizes stream events into message `steps` for the UI
  - persists UI preferences (trace visibility, raw reasoning toggle)

## Backend Event Types

The frontend consumes events from the backend's event mapping system. Key event categories:

| Event Category    | Description             | UI Handler                |
| ----------------- | ----------------------- | ------------------------- |
| `reasoning`       | DSPy reasoning steps    | Thought bubbles, progress |
| `routing`         | Agent routing decisions | Workflow visualization    |
| `analysis`        | Task analysis phase     | Task breakdown view       |
| `quality`         | Quality assessment      | Score display             |
| `agent_output`    | Agent response chunks   | Message streaming         |
| `workflow_status` | Pipeline phase changes  | Status indicators         |

## Adding New Event Handling

When backend adds streaming event types:

1. Backend: Update `api/v1/events/mapping.py`
2. Backend: Add `ui_routing:` entry in `workflow_config.yaml`
3. **Frontend**: Update `src/api/types.ts` (types)
4. **Frontend**: Handle in `src/features/chat/stores/chatStore.ts` (event handling/mapping)
5. **Frontend**: Add tests under `src/tests/`

## UI Guidelines

- Keep pages thin (validate/select state + compose components).
- Prefer feature UI under `src/features/*` and reusable atoms under `src/components/ui/*`.
- Use `motion/react` for animations, NOT `framer-motion`.
- Follow the design tokens in `src/styles/` for consistent theming.

## API Configuration

- `VITE_API_URL` in `.env` (defaults to `http://localhost:8000`)
- All API calls go through `src/api/` layer—never direct fetch
- SSE endpoints: `/api/chat/:id/stream`
- REST endpoints: `/api/v1/*`

## Testing

```bash
make test-frontend               # Run Vitest tests
cd src/frontend && npm run test:ui  # Interactive test UI
```
