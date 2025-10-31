# AGENTS.md

## Overview

The frontend is a Vite 5 + React 18 application using TypeScript, shadcn/ui components, Tailwind utilities, and SSE streams from the FastAPI backend. It lives entirely in this folder and expects the backend API at `http://localhost:8000/v1`. Anything that mutates chat state, renders streaming responses, or touches shared UI primitives belongs here.

## Environment & Setup

1. Install Node.js 20+ (the repo assumes npm 10+). If you are using Volta or nvm, pin to the version declared in `.tool-versions` when available.
2. Install dependencies once via `npm install` (or from repo root with `make frontend-install`).
3. Ensure the backend is running (`make dev` or `uv run uvicorn agentic_fleet.server:app --reload --port 8000`) before exercising API-dependent features.
4. Environment variables for the frontend reside in `src/frontend/.env` (not committed). Copy `index.html` meta tags or `vite.config.ts` aliases carefully if you need additional variables; Vite requires them to be prefixed with `VITE_`.

## Development Commands

- Start hot reload: `npm run dev` (defaults to port 5173). Use `npm run dev -- --host` when testing from other devices.
- Build for production: `npm run build` emits static assets in `dist/`.
- Preview built assets locally: `npm run preview -- --port 5173`.
- Format code: `npm run format` (prettier over the entire tree).
- Linting is currently a stub (`npm run lint`), so rely on TypeScript and editor tooling; update the script before enabling additional linters.

## Testing Strategy

- Component and hook tests use Vitest with React Testing Library. Run `npm run test` for a one-off pass or `npm run test -- --watch` for interactive mode.
- Tests requiring DOM APIs rely on jsdom; avoid using browser-only globals unless they are polyfilled in `src/frontend/test/setup.ts`.
- Keep network calls mocked. Hooks such as `useChatClient` wrap API fetches; expose the HTTP layer through dependency injection if you need deterministic tests.

## UI & State Conventions

- Shared primitives live under `src/components/ui/`; extend them rather than duplicating markup in feature-level components.
- Feature code (e.g. `features/chat/`) combines hooks (`useChatController.ts`) with presentational components. Maintain this split to avoid large, stateful monoliths.
- Tailwind is configured in `tailwind.config.ts`; favor utility classes with `tailwind-merge` helpers, and avoid inline styles except for dynamic values that cannot be expressed via classes.
- Syntax highlighting leverages Shiki; when adding languages, update `src/components/ui/code-block.tsx` accordingly.

## API Integration Notes

- All HTTP calls flow through the chat client utilities in `features/chat/`. Respect the existing SSE parsing logic in `response-stream.tsx`; new endpoints should follow the same incremental chunk handling.
- Backend routes live under `/v1/...`. Keep URL literals centralized in `useChatClient.ts` to make future rewrites easier.
- When adjustments require backend changes, coordinate with `src/agentic_fleet/AGENTS.md` policies—especially around workflow IDs and approval flows.

## Quick Reference

- `npm install` — Install dependencies.
- `npm run dev` — Start the Vite dev server.
- `npm run test` — Run Vitest suite.
- `npm run test -- --watch` — Watch mode for tests.
- `npm run build` — Generate production bundle in `dist/`.
- `npm run preview -- --port 5173` — Serve built assets locally.
- `npm run format` — Format source files with Prettier.

## Troubleshooting

- Blank screen during development? Check the browser console for CORS errors—ensure the backend is running on port 8000 and that the CORS middleware allows `http://localhost:5173`.
- SSE stream stalls typically mean the backend cancelled the workflow; inspect the Network tab for `event: error` payloads.
- TypeScript path resolution issues? Run `npm install` again to refresh `node_modules/@types`, then restart `tsc --watch` or your editor's language server.
- If UI assets look outdated after dependency upgrades, delete `.vite` cache and rerun `npm run dev`.
