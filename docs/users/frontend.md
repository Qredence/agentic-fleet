# Frontend Guide

## Overview

AgenticFleet includes a React-based web interface for interacting with the multi-agent system. The frontend provides:

- Real-time chat interface with streaming responses
- Workflow visualization showing agent orchestration
- Chain-of-thought and reasoning display
- Conversation history management

## Quick Start

### Starting the Frontend

The easiest way to start the frontend is with Make:

```bash
# Start both backend and frontend
make dev
```

This starts:

- **Backend**: http://localhost:8000 (FastAPI)
- **Frontend**: http://localhost:5173 (Vite dev server)

### Using Make

```bash
make dev            # Both servers
make backend        # Backend only (port 8000)
make frontend-dev   # Frontend only (port 5173)
```

## Features

### Chat Interface

The main chat interface allows you to:

- Send messages to the multi-agent system
- View streaming responses in real-time
- See which agents are processing your request
- Access conversation history

### Workflow Visualization

During message processing, the UI displays:

- **Orchestrator thoughts**: Routing decisions, task analysis
- **Agent activity**: Which agents are working and their outputs
- **Reasoning steps**: Chain-of-thought reasoning (for GPT-5 models)
- **Quality scores**: Assessment of response quality

### Conversation Management

- Create new conversations
- Switch between existing conversations
- Conversations persist across sessions (stored in `.var/data/conversations.json`)

## Configuration

### Environment Variables

Frontend-specific configuration in `.env`:

```bash
# Backend API URL (for production deployments)
VITE_API_URL=http://localhost:8000
```

The `/api` prefix is added automatically by the frontend.

### CORS Configuration

For production deployments, configure allowed origins in the backend:

```bash
# In .env
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

## Development

### Installing Dependencies

```bash
# From project root
make frontend-install

# Or directly
cd src/frontend && npm install
```

### Running Tests

```bash
# Unit tests
make test-frontend

# E2E tests (requires dev servers running)
make test-e2e
```

### Linting and Formatting

```bash
make frontend-lint    # ESLint
make frontend-format  # Prettier
```

### Building for Production

```bash
make build-frontend
```

This builds the frontend and copies assets to `src/agentic_fleet/ui/` for serving by the backend.

## Architecture

The frontend uses:

- **React 19** with TypeScript
- **Vite** for development and building
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **Server-Sent Events (SSE)** for real-time streaming (recommended)

### Key Files

| Path                                    | Purpose                                   |
| --------------------------------------- | ----------------------------------------- |
| `src/frontend/src/root/App.tsx`         | App shell + routing                       |
| `src/frontend/src/stores/chatStore.ts`  | Chat state management and streaming logic |
| `src/frontend/src/api/sse.ts`           | SSE client for chat streaming             |
| `src/frontend/src/api/client.ts`        | REST API client                           |
| `src/frontend/src/api/types.ts`         | TypeScript type definitions               |
| `src/frontend/src/components/chat/`     | Chat and message rendering components     |
| `src/frontend/src/components/workflow/` | Workflow visualization components         |

### SSE Streaming Protocol (Recommended)

The frontend streams events via SSE at `/api/chat/{conversation_id}/stream`:

1. Client opens an SSE connection with query params (`message`, `reasoning_effort`, `enable_checkpointing`)
2. Server streams `StreamEvent` messages
3. If the workflow emits a human-in-the-loop request, the client submits a response via REST:
   - `POST /api/chat/{conversation_id}/respond?workflow_id=...`
4. Client can cancel via REST:
   - `POST /api/chat/{conversation_id}/cancel?workflow_id=...`
5. Server emits `{type: "done"}` when complete

Checkpoint semantics (agent-framework):

- `enable_checkpointing=true` enables checkpoint storage on the server.
- Resume is supported via the legacy WebSocket endpoint (`/api/ws/chat`) using `workflow.resume`.

### Message Flow Diagrams

These diagrams show the expected message flow for the web UI. They are intentionally aligned with agent-framework semantics:

- **New run** uses `message` (and may opt into `enable_checkpointing`)
- **HITL (SSE)** uses the REST `respond` endpoint to unblock execution
- **Resume** uses `checkpoint_id` only via legacy WebSocket

#### New Run (Streaming via SSE)

```mermaid
sequenceDiagram
	participant U as User
	participant FE as Frontend (Web UI)
	participant SSE as Backend SSE (/api/chat/{conversation_id}/stream)
	participant WF as Supervisor Workflow

	U->>FE: Type message + send
	FE->>SSE: GET stream?message=...&enable_checkpointing=...
	SSE->>WF: run_stream(message)

	loop Stream events
		WF-->>SSE: StreamEvent
		SSE-->>FE: StreamEvent
		FE-->>U: Render tokens/steps
	end

	WF-->>SSE: done
	SSE-->>FE: {type: "done"}
```

#### Human-in-the-Loop (HITL) Request + Response

```mermaid
sequenceDiagram
	participant FE as Frontend (Web UI)
	participant SSE as Backend SSE (/api/chat/{conversation_id}/stream)
	participant WF as Supervisor Workflow

	WF-->>SSE: request event (needs user input)
	SSE-->>FE: StreamEvent {type: "request", ...}

	FE->>SSE: POST /api/chat/{conversation_id}/respond?workflow_id=...
	SSE->>WF: forward response

	loop Stream events
		WF-->>SSE: StreamEvent
		SSE-->>FE: StreamEvent
	end

	WF-->>SSE: done
	SSE-->>FE: {type: "done"}
```

#### Resume from a Checkpoint (WebSocket legacy)

```mermaid
sequenceDiagram
	participant FE as Frontend (Web UI)
	participant WS as Backend WS (/api/ws/chat)
	participant WF as Supervisor Workflow

	FE->>WS: {type: "workflow.resume", checkpoint_id}
	WS->>WF: resume(checkpoint_id)

	loop Stream events
		WF-->>WS: StreamEvent
		WS-->>FE: StreamEvent
	end

	WF-->>WS: done
	WS-->>FE: {type: "done"}
```

See `src/frontend/AGENTS.md` for detailed frontend architecture documentation.

## Troubleshooting

### Frontend Not Loading

1. Ensure dependencies are installed: `make frontend-install`
2. Check that port 5173 is available
3. Verify backend is running if using `make frontend-dev`

### SSE Connection Failed

1. Check that backend is running on the expected port
2. Verify CORS settings allow your origin
3. Check browser console for specific errors

### Styles Not Applying

1. Run `npm install` to ensure Tailwind is installed
2. Check `tailwind.config.js` for correct content paths

### Hot Reload Not Working

1. Restart the dev server: `make dev`
2. Clear browser cache
3. Check for syntax errors in modified files

## Next Steps

- See [Quick Reference](../guides/quick-reference.md) for all commands
- Read [Frontend AGENTS.md](../../src/frontend/AGENTS.md) for detailed architecture
- Check [Configuration](configuration.md) for backend settings
