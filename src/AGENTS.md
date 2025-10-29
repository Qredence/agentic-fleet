# AGENTS.md – src/

> Agent-focused guide for working in the `src/` directory. This directory contains both the Python backend (`agenticfleet/`) and React frontend (`frontend/`). For detailed subproject instructions, see nested AGENTS.md files.

---

## Directory Structure

```
src/
├── agenticfleet/           # Python backend package
│   ├── __init__.py
│   ├── server.py          # FastAPI application
│   ├── workflow.py        # Workflow orchestration
│   ├── agents/           # Agent implementations
│   ├── api/              # API models and handlers
│   ├── cli/              # CLI tools
│   ├── memory/           # Memory integration (Mem0)
│   └── persistance/      # Database layer
│
└── frontend/             # React + Vite frontend
    ├── src/              # Frontend source
    ├── package.json      # npm dependencies
    ├── vite.config.ts    # Build configuration
    └── AGENTS.md         # Frontend-specific guide
```

---

## Quick Navigation

**Working on backend?** → See `agenticfleet/AGENTS.md`
**Working on frontend?** → See `frontend/AGENTS.md`

---

## Common Commands (from repository root)

### Backend Development

```bash
# Install Python dependencies
make install

# Run backend only
make backend

# Run full stack (backend + frontend)
uv run agentic-fleet
# OR
make dev
```

### Frontend Development

```bash
# Install frontend dependencies
make frontend-install

# Run frontend only
cd src/frontend && npm run dev

# Lint frontend
cd src/frontend && npm run lint
```

### Testing

```bash
# Run all tests
make test

# Validate configuration
make test-config

# Run specific backend test
uv run pytest tests/test_workflow.py -v

# Type check backend
make type-check
```

### Code Quality

```bash
# All checks (lint + type)
make check

# Format code
make format

# Lint only
make lint
```

---

## Integration Points

The two subprojects integrate at these boundaries:

1. **FastAPI Server** (`agenticfleet/server.py`):
   - Serves REST API endpoints
   - Provides WebSocket streaming for real-time chat
   - Handles HITL approval requests

2. **API Models** (`agenticfleet/api/models/`):
   - Pydantic models define contract between backend and frontend
   - Event types for WebSocket streaming
   - Request/response schemas

3. **Frontend API Client** (`frontend/src/lib/`):
   - Consumes backend REST endpoints
   - Handles WebSocket connection and event parsing
   - Type-safe integration via TypeScript interfaces

---

## Development Workflow

### Full Stack Development

1. Start backend and frontend together:

   ```bash
   make dev
   ```

   - Backend: <http://localhost:8000>
   - Frontend: <http://localhost:5173>

2. Make changes in either subproject

3. Watch for:
   - Backend: Auto-reload via uvicorn
   - Frontend: HMR via Vite

### Backend-Only Development

```bash
# Start backend
make backend

# Test with curl or API client
curl http://localhost:8000/health
```

### Frontend-Only Development

```bash
# Terminal 1: Start backend
make backend

# Terminal 2: Start frontend
cd src/frontend && npm run dev
```

---

## Before Committing

Run these checks from repository root:

```bash
# Validate configuration
make test-config

# Code quality checks
make check

# Run tests
make test

# Frontend lint
cd src/frontend && npm run lint
```

---

## File Organization Rules

### Backend (`agenticfleet/`)

- **DO**: Use `uv run` for all Python commands
- **DO**: Define types with Pydantic models
- **DO**: Keep configuration in YAML files
- **DON'T**: Hardcode model names or API endpoints
- **DON'T**: Use `pip` directly (use `uv` instead)

### Frontend (`frontend/`)

- **DO**: Use TypeScript for all new files
- **DO**: Import from `@/` path alias
- **DO**: Follow shadcn/ui component patterns
- **DON'T**: Modify `ui/shadcn/` components directly
- **DON'T**: Hardcode backend URLs (use env vars)

---

## API Contract Changes

When changing the backend-frontend contract:

1. **Update Backend**:
   - Modify Pydantic models in `api/models/`
   - Update server endpoints in `server.py`
   - Add/update tests

2. **Update Frontend**:
   - Update TypeScript types in `lib/types.ts`
   - Modify API client calls
   - Update event handlers if streaming changes

3. **Test Integration**:
   - Run full stack: `make dev`
   - Test WebSocket streaming
   - Verify HITL approval flow

4. **Document**:
   - Update relevant AGENTS.md files
   - Add comments for breaking changes

---

## Troubleshooting

### Backend won't start

- Check: Python version >= 3.12
- Check: `uv` installed and in PATH
- Run: `make sync` to update dependencies
- Check: `.env` file exists with required keys

### Frontend won't build

- Check: Node.js version >= 18
- Run: `cd src/frontend && npm install`
- Check: Backend running (if testing API calls)
- Clear cache: `rm -rf src/frontend/node_modules/.vite`

### Integration issues

- Verify backend running on correct port (8000)
- Check CORS settings in `server.py`
- Inspect browser network tab for errors
- Check backend logs: `tail -f var/logs/agenticfleet.log`

---

## Additional Resources

- **Backend Details**: `agenticfleet/AGENTS.md`
- **Frontend Details**: `frontend/AGENTS.md`
- **Root Guide**: `../AGENTS.md` (repository root)
- **Architecture**: `../docs/architecture/`
- **API Reference**: Start backend and visit <http://localhost:8000/docs>
