# AgenticFleet Frontend

React + Vite + TypeScript frontend for AgenticFleet multi-agent orchestration system.

## Features

- 🤖 **Chatbot Interface**: Beautiful chat UI from [prompt-kit](https://prompt-kit.com)
- ⚡ **Real-time Streaming**: SSE-based streaming from FastAPI backend
- 🎨 **Modern UI**: Tailwind CSS + shadcn/ui components
- 🔥 **Fast Development**: Vite HMR for instant updates

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server (with FastAPI proxy)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Architecture

```
Frontend (Vite + React)     FastAPI Backend (HaxUI)
┌─────────────────────┐     ┌──────────────────────┐
│                     │     │                      │
│  AgenticFleet       │────▶│  /v1/responses       │
│  Chatbot            │     │  (SSE streaming)     │
│                     │     │                      │
│  - useFastAPIChat   │     │  MagenticFleet       │
│  - Message UI       │     │  Orchestrator        │
│  - Input Handler    │     │                      │
└─────────────────────┘     └──────────────────────┘
```

## Integration with FastAPI

The frontend connects to FastAPI HaxUI endpoints:

- **`POST /v1/responses`**: Send messages and receive SSE streams
- **`GET /v1/conversations`**: List conversation history
- **`GET /health`**: Check backend status

Vite proxy config (`vite.config.ts`) automatically forwards `/v1/*` and `/health` to `http://localhost:8000`.

## Components

### Main Chatbot Component

- `src/components/agenticfleet-chatbot.tsx`: Full chatbot UI
- `src/lib/use-fastapi-chat.ts`: Custom React hook for FastAPI SSE

### Prompt-Kit Components (from shadcn)

- `src/components/prompt-kit/chat-container.tsx`: Chat layout
- `src/components/prompt-kit/message.tsx`: Message bubbles
- `src/components/prompt-kit/prompt-input.tsx`: Input with actions
- `src/components/prompt-kit/markdown.tsx`: Markdown rendering
- `src/components/prompt-kit/code-block.tsx`: Code syntax highlighting
- `src/components/prompt-kit/loader.tsx`: Loading indicators

### UI Components (shadcn/ui)

- `src/components/ui/button.tsx`
- `src/components/ui/avatar.tsx`
- `src/components/ui/tooltip.tsx`
- `src/components/ui/textarea.tsx`

## Development

### Starting the Full Stack

```bash
# Terminal 1: Start FastAPI backend
cd /path/to/AgenticFleet
uv run python -m agenticfleet.haxui.runtime  # or uvicorn command

# Terminal 2: Start Vite dev server
cd src/frontend
npm run dev
```

Open http://localhost:5173 to see the chatbot.

### Customization

**Change model/agent:**

```tsx
<AgenticFleetChatbot
  model="researcher" // or "coder", "analyst", "magentic_fleet"
  placeholder="Ask the researcher..."
/>
```

**Add conversation context:**

```tsx
<AgenticFleetChatbot conversationId="conv_abc123" model="magentic_fleet" />
```

## Building for Production

```bash
npm run build
```

Output: `dist/` directory with static files ready for deployment.

### Deployment Options

1. **Serve from FastAPI**: Copy `dist/` to `src/agenticfleet/haxui/ui/` and serve via FastAPI static files
2. **CDN/Static Host**: Deploy `dist/` to Vercel, Netlify, Cloudflare Pages, etc.
3. **Nginx/Apache**: Serve `dist/` with reverse proxy to FastAPI backend

## License

MIT
