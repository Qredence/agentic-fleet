# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup

```bash
# Full development setup (install + frontend + pre-commit)
make dev-setup

# Install Python dependencies with uv
make install

# Install frontend dependencies
make frontend-install
```

### Running the Application

```bash
# Full stack development (backend + frontend)
make dev
# Alternative: uv run agentic-fleet

# Backend only (port 8000)
make backend

# Frontend only (port 5173)
make frontend-dev
```

### Testing

```bash
# Run all tests
make test

# Run configuration validation
make test-config

# Run end-to-end tests (requires dev running)
make test-e2e
```

### Code Quality

```bash
# Run all quality checks (lint + type-check)
make check

# Individual checks
make lint          # Ruff linter
make format        # Black + Ruff formatting
make type-check    # MyPy strict type checking
```

### Build

```bash
# Build frontend for production (outputs to backend/ui)
make build-frontend
```

## Architecture Overview

AgenticFleet is a multi-agent orchestration system built on Microsoft Agent Framework's Magentic One pattern with two main components:

### Backend Architecture (`src/agentic_fleet/`)

**Core Components:**

- **API Layer** (`api/`): FastAPI application with modular routes for chat, workflows, approvals, conversations, entities, responses, and system endpoints
- **Core Workflow Engine** (`core/`): Contains `MagenticFleetWorkflow`, `MagenticBuilder`, and agent orchestration logic
- **CLI Interface** (`cli/`): Rich terminal interface for direct agent interaction
- **Integrations**: MCP server support and Mem0 memory integration

**Key Workflow Patterns:**

1. **Dynamic Orchestration** (default): Manager spawns specialist agents (planner, executor, coder, verifier, generator) on-demand based on task requirements
2. **Reflection Pattern**: Worker-reviewer iterative refinement

**Configuration System:**

- YAML-based workflow configuration in `config/workflows.yaml`
- Per-agent configurations with role-specific instructions and tools
- WorkflowFactory pattern for loading and validating workflows

### Frontend Architecture (`src/frontend/src/`)

**Technology Stack:**

- React 18.3+ with TypeScript
- Vite 7.x for build tooling
- shadcn/ui components with Tailwind CSS
- React Hook Form with Zod validation
- React Query for data fetching
- Zustand for state management

**Key Features:**

- Modern chat interface with agent-as-workflow pattern
- Real-time streaming responses via SSE
- Custom hook architecture for maintainable state management
- Component-based design with shadcn prompt-kit integration

## Development Patterns

### Backend Development

- Use **uv** for all Python package management
- All API routes follow FastAPI patterns with Pydantic schemas
- Configuration validation through `WorkflowFactory`
- Mock `OpenAIResponsesClient` in tests to avoid API costs
- Strict typing required (MyPy 100% compliance)

### Frontend Development

- Components organized by feature (`features/chat/`) and shared UI (`components/ui/`)
- Custom hooks extracted for state management (see `useChatClient`, `useChatController`)
- API communication through typed client libraries
- Non-streaming HTTP responses with async updates

### Testing Strategy

- Configuration tests validate YAML structure and agent factories
- Fleet tests cover orchestration scenarios (14 test cases)
- Frontend testing with Vitest and React Testing Library
- Always mock external API calls

## Key Files and Locations

### Configuration

- `config/workflows.yaml` - Main workflow configuration
- `pyproject.toml` - Python dependencies and project metadata
- `src/frontend/src/package.json` - Frontend dependencies

### Core Backend

- `src/agentic_fleet/core/magentic_workflow.py` - Main workflow engine
- `src/agentic_fleet/api/workflow_factory.py` - Workflow loading and validation
- `src/agentic_fleet/api/app.py` - FastAPI application setup

### Frontend Core

- `src/frontend/src/features/chat/ChatPage.tsx` - Main chat interface
- `src/frontend/src/features/chat/useChatClient.ts` - API communication logic
- `src/frontend/src/features/chat/useChatController.ts` - UI state management

## Environment Requirements

- **Python 3.12+** with uv package manager
- **Node.js/npm** for frontend development
- **OpenAI API key** (set as `OPENAI_API_KEY`)
- Optional: Mem0 integration for long-term memory
- Optional: OpenTelemetry for observability

## Agent Configuration

Agents are configured declaratively in YAML with the following structure:

- **planner**: Breaks down complex requests into actionable steps
- **executor**: Executes plan steps and coordinates specialists
- **coder**: Writes and executes code with hosted interpreter tool
- **verifier**: Validates intermediate outputs and quality checks
- **generator**: Synthesizes verified work into final responses

Each agent can be configured with specific models, temperature, tools, and instructions through the workflow configuration system.
