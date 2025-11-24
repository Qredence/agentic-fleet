# AgenticFleet Frontend

The official frontend for the AgenticFleet framework, built with React, TypeScript, and Vite.

## Features

- **Real-time Chat**: Interaction with AI agents via streaming responses.
- **Conversation Management**: Create, list, and switch between multiple conversations.
- **Orchestrator Visibility**: View internal agent reasoning and orchestration steps.
- **Modern UI**: Clean interface built with Tailwind CSS and Radix UI primitives.

## Getting Started

### Prerequisites

- Node.js (v18+)
- Backend running on `http://localhost:8000` (see root README)

### Installation

```bash
cd src/frontend
npm install
```

### Development

```bash
npm run dev
```

Access the app at `http://localhost:5173`.

### Testing

Run the test suite:

```bash
npm test
```

## Documentation

For a detailed walkthrough of the codebase and UI features, see [WALKTHROUGH.md](./WALKTHROUGH.md).

## Project Structure

- `src/components/`: UI components (Chat, Sidebar, etc.)
- `src/stores/`: Global state (Zustand)
- `src/lib/`: Utilities and API clients
- `src/hooks/`: React hooks

## License

See the root LICENSE file.
