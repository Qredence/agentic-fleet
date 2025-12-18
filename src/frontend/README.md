# AgenticFleet Frontend

Vite + React 19 + TypeScript + Tailwind CSS v4 chat UI for AgenticFleet.

## Development

`# from repo root`

- Install deps: `make frontend-install`
- Run frontend: `make frontend-dev` (http://localhost:5173)
- Run full stack: `make dev` (backend http://localhost:8000 + frontend)

## Environment

- `VITE_API_URL` (optional): backend origin (default `http://localhost:8000`)

In development, Vite proxies `/api/*` to the backend.

## UI Notes

- **Process / reasoning transparency**: the chat header includes toggles for showing the process trace and (optionally) raw reasoning.
- **shadcn/ui primitives** live under `src/frontend/src/components/ui`.
- **Design system** lives in `src/frontend/src/index.css` and `src/frontend/src/styles/*`.

## Testing

`# from repo root`

- Unit tests: `make test-frontend`
- Lint: `make frontend-lint`
- Build: `make build-frontend`
