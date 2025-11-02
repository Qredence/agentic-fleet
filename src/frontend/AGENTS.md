# Frontend Overview

`src/frontend/` is the staging area for the React/Vite client. The actual application lives under `src/frontend/src`, while this directory keeps build artifacts (`dist/`), the local npm lockfile, and documentation for contributors. Production builds end up in `src/agentic_fleet/ui/` so the FastAPI backend can serve the SPA.

## Layout

- `src/frontend/src/` — Vite project (see `src/frontend/src/AGENTS.md` for deep-dive guidance, component ownership, and testing strategy).
- `dist/` — Latest build output from `npm run build` (cleaned & re-created as part of release flows).
- `node_modules/` — Installed dependencies for the outer workspace (mainly shadcn tooling). The Vite project maintains its own `node_modules` inside `src/frontend/src/`.
- `AGENTS.md` (this file) — High-level instructions; defer to nested docs for implementation details.

## Commands

- `make frontend-install` — Runs `npm install` inside `src/frontend/src`. Always execute this after cloning or whenever `package.json` changes.
- `make frontend-dev` — Starts `npm run dev` in `src/frontend/src` (Vite dev server on port 5173).
- `make build-frontend` — Builds the UI (`npm run build`) and copies the output into `src/agentic_fleet/ui/` for FastAPI to serve.
- `npm run lint`, `npm run test`, `npm run format` — Run from `src/frontend/src` when working directly in that directory.
- Full stack development remains `make dev`, which spins up both backend and frontend with hot reload.

## Coordination with the backend

- The UI consumes the OpenAI-compatible Responses API served from `/v1/responses`. Schema changes must stay synchronized with `src/agentic_fleet/api/responses/` and the bridge in `src/agentic_fleet/workflow/events.py`.
- Configuration-driven workflows surface through `/v1/entities`; if you add a new workflow ID in YAML, update the frontend entity queries (`src/frontend/src/lib/queries/entityQueries.ts`) accordingly.
- Production builds need the backend running with the `ui/` directory in place. After `make build-frontend`, verify that `uv run uvicorn agentic_fleet.server:app --reload` serves the Vite assets locally.

## Quality gates

- Keep React changes aligned with `src/frontend/src/AGENTS.md` guidance (shadcn/ui conventions, Zustand stores, SSE handling).
- Run `npm run lint` and `npm run test` within `src/frontend/src` for any UI-affecting change; capture Vitest coverage with `npm run test:coverage` when appropriate.
- Remember to run `uv run python tools/scripts/validate_agents_docs.py` after editing this or any nested AGENTS documentation.

## When to update this file

- Document new top-level build commands, dependency flows, or deviations in the layout of `src/frontend/`.
- Cross-link to new deep-dive docs living under `src/frontend/src/` whenever the substructure changes (e.g., new feature areas, store reorganisations).
- Note interactions with backend deployments (e.g., additional static assets or environment variables) so agents updating the backend know where to look.
