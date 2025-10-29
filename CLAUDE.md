# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Overview

**AgenticFleet** is a multi-agent orchestration system built on Microsoft Agent Framework's Magentic One pattern. It features a manager-executor architecture where specialized agents (orchestrator, researcher, coder, analyst) collaborate on complex tasks through structured planning and dynamic delegation. The system provides three interfaces: a React web frontend (default), a rich CLI, and Jupyter notebooks for experimentation.

## Key Commands

### Setup & Dependencies

```bash
# First-time setup (Python + frontend)
make install && make frontend-install

# Update dependencies after lockfile changes
make sync

# Validate configuration (CRITICAL after any YAML changes)
make test-config
```

### Development

```bash
# Full stack development (backend on :8000, frontend on :5173)
make dev

# Backend only
make haxui-server

# Frontend only
make frontend-dev

# Run the CLI application
uv run fleet
```

### Code Quality

```bash
# Run all quality checks (lint + type-check)
make check

# Individual checks
make lint          # Ruff linting
make format        # Black + Ruff formatting
make type-check    # MyPy strict checks

# Run tests
make test

# Validate agent documentation invariants
make validate-agents
```

## MCP Servers

AgenticFleet includes Model Context Protocol (MCP) servers for enhanced capabilities:

### Available MCP Servers

**DeepGraph React MCP**
- Provides code analysis and understanding of the React codebase
- Located at: `facebook/react` repository
- Tools for navigating React components and architecture

**Prompt-Kit Registry**
- Access to shadcn/ui component registry
- Provides enhanced UI components for AI interfaces
- Configuration: `shadcn@canary` with registry endpoint

**Playwright MCP Server** ⭐ **NEW**
- Browser automation and testing capabilities
- Web scraping and content extraction
- Screenshot capture and visual testing
- Form interaction and user simulation
- Test code generation and execution

### Installing Playwright MCP

```bash
# Install globally
npm install -g @executeautomation/playwright-mcp-server

# Test installation
./scripts/test-playwright-mcp.sh

# Install Playwright browsers (if needed)
npx playwright install
```

### MCP Configuration

MCP servers are configured in `.mcp.json`:

```json
{
  "mcpServers": {
    "playwright": {
      "description": "Playwright MCP server for browser automation and testing",
      "command": "npx",
      "args": ["-y", "@executeautomation/playwright-mcp-server"]
    }
  }
}
```

### Using Playwright MCP Tools

Once configured, the Playwright MCP server provides tools for:

```bash
# Navigate to websites
playwright_navigate --url="https://example.com"

# Take screenshots
playwright_screenshot --path="./screenshot.png"

# Extract content
playwright_get_content --type="text"

# Interactive automation
playwright_click --selector="#submit-button"
playwright_type --selector="#search" --text="query"
```

**Documentation**: See `docs/setup/playwright-mcp-setup.md` for complete setup guide.

## Architecture Overview

### Core Pattern: Magentic One Workflow

The system implements Microsoft's Magentic One pattern with a sophisticated **Manager-Executor** architecture:

1. **PLAN** - Manager analyzes task, creates structured action plan with facts and steps
2. **EVALUATE** - Progress ledger determines task satisfaction, loop detection, and next speaker
3. **ACT** - Selected specialist executes with domain-specific tools and capabilities
4. **OBSERVE** - Manager reviews responses, updates context, and determines continuation
5. **REPEAT** - Cycle continues until completion or limits are reached

### YAML-Driven Workflow Configuration

The system features two primary workflows defined in `src/agenticfleet/magentic_fleet.yaml`:

1. **Collaboration Workflow** - Three-agent team (researcher, coder, reviewer)
2. **Magentic Fleet Workflow** - Five-agent orchestration (planner, executor, coder, verifier, generator)

Each workflow configures:
- Agent models (default: gpt-5-mini)
- Custom instructions and reasoning parameters
- Temperature and token limits
- Tool enablement per agent
- Manager coordination settings

### Event-Driven Architecture

The orchestration is fundamentally event-driven, with real-time streaming of:

- `MagenticAgentDeltaEvent` - Streaming token outputs for real-time UI updates
- `MagenticAgentMessageEvent` - Complete agent responses with metadata
- `RequestInfoEvent` - Human-in-the-loop plan review requests
- `WorkflowOutputEvent` - Final workflow results

The `ConsoleCallbacks` class acts as an event router, bridging Microsoft Agent Framework events to CLI UI, frontend SSE streams, and audit logging systems.

### Agent Specialists

The system supports both static and dynamic agent configurations:

**Foundation Agents (configurable models):**
- **Planner**: Task decomposition and step assignment
- **Executor**: Implementation coordination and reasoning-heavy steps
- **Coder**: Code generation and execution with HostedCodeInterpreterTool
- **Verifier**: Quality assurance and output validation
- **Generator**: Final response synthesis and user-facing answers

**Legacy Agents (for reference):**
- **Orchestrator**: Task planning & result synthesis (`gpt-5`)
- **Researcher**: Information gathering & citations (`gpt-5`)
- **Analyst**: Data exploration & insights (`gpt-5`)

### Configuration Files

- **Workflow Config**: [`src/agenticfleet/magentic_fleet.yaml`](src/agenticfleet/magentic_fleet.yaml) - YAML-driven workflow definitions
- **Frontend Config**: [`src/frontend/package.json`](src/frontend/package.json) - React app with Vite 7.x and shadcn/ui
- **Project Config**: [`pyproject.toml`](pyproject.toml) - Python dependencies, tool configs, and Microsoft Agent Framework integration
- **MCP Config**: [`.mcp.json`](.mcp.json) - Model Context Protocol server configurations

### Technology Stack

- **Backend**: Python 3.12+, Microsoft Agent Framework, FastAPI, Pydantic, Azure AI integration
- **Frontend**: React 18.3+, TypeScript, Vite 7.x, shadcn/ui, Tailwind CSS
- **Package Management**: `uv` for Python dependencies, npm for frontend dependencies
- **Communication**: Server-Sent Events (SSE) for real-time streaming between backend and frontend
- **Build System**: Hatchling for Python packages, Vite for frontend assets

## Critical Development Patterns

### uv-First Workflow

ALL Python commands MUST use `uv run` prefix:

- `uv run python -m agenticfleet` (not `python main.py`)
- `uv run pytest` (not `pytest`)
- `uv run python tests/test_config.py`

### Configuration-Driven Architecture

- **YAML is source of truth** - All workflow definitions in `magentic_fleet.yaml`
- **Never hardcode models** - Read from YAML configuration files
- **Manager instructions** defined in workflow configuration under manager sections
- **Environment variables** via `.env` for API keys and sensitive configuration
- **Workflow Factory Pattern** - Dynamic workflow creation via `create_collaboration_workflow()` and `create_magentic_fleet_workflow()` functions

### Hierarchical Configuration Architecture

```text
Environment Variables (.env)
    ↓
Global Workflow Config (magentic_fleet.yaml)
    ↓
Agent Factory Functions (workflow.py)
    ↓
Runtime Settings (settings.py)
```

### Tool Development Pattern

1. Tools enabled per agent in YAML configuration (`tools:` section)
2. **HostedCodeInterpreterTool** for code execution and analysis
3. Enable/disable via workflow YAML configuration
4. For sensitive operations, use HITL approval system

### Workflow Factory Pattern

```python
def create_collaboration_workflow() -> Workflow:
    # Three-agent workflow: researcher, coder, reviewer
    builder = MagenticBuilder().participants(
        researcher=researcher,
        coder=coder,
        reviewer=reviewer,
    ).with_standard_manager(...)
    return builder.build()

def create_magentic_fleet_workflow() -> Workflow:
    # Five-agent workflow: planner, executor, coder, verifier, generator
    builder = MagenticBuilder().participants(
        planner=planner,
        executor=executor,
        coder=coder,
        verifier=verifier,
        generator=generator,
    ).with_standard_manager(...)
    return builder.build()
```

## Advanced Architecture Patterns

### Vite 7.x Frontend Architecture

The frontend has been successfully migrated to Vite 7.x with modern development patterns:

- **Feature-based organization**: Components organized by domain/feature in `src/components/features/`
- **Type-safe API integration**: Full TypeScript coverage with strict typing and comprehensive error handling
- **Real-time streaming**: SSE integration via `useFastAPIChat.ts` hook with robust retry logic
- **Modern build tooling**: Vite 7.1.12 for optimized development and production builds
- **Component library**: Comprehensive shadcn/ui integration with Radix UI primitives
- **Hook-based architecture**: Extracted custom hooks for maintainable state management
- **Production-grade error handling**: Exponential backoff retry logic across all API operations

### Dynamic Agent Spawning

The system supports dynamic orchestration with on-demand agent creation:

- **Foundation Agents**: Planner, Executor, Generator, Verifier with configurable models
- **Model Pool**: Tiered model selection (gpt-5, gpt-5-codex, gpt-5-mini, gpt-5-nano)
- **Spawn Limits**: Configurable bounds on agent creation and nesting depth
- **Real-time Events**: SSE streaming of spawn events to frontend

### Event-Driven Callbacks and Observability

The `ConsoleCallbacks` system routes events to multiple destinations:

1. **CLI Console**: Real-time streaming output for terminal users
2. **Frontend SSE**: Server-Sent Events for React web interface
3. **Audit Logging**: Structured JSON logs for compliance and debugging
4. **OpenTelemetry**: Distributed tracing for observability

### Multi-Channel Event Routing

Events are routed intelligently based on configuration:

- **streaming_enabled**: Real-time token streaming for better UX
- **log_progress_ledger**: Manager's reasoning and decision tracking
- **log_tool_calls**: Comprehensive audit trail of tool executions

## Testing Patterns

### Configuration Validation

ALWAYS run after YAML changes:

```bash
uv run python tests/test_config.py
```

This validates env vars, agent structure, tool imports, and factory callables.

### Test Organization

- `tests/test_config.py` - Configuration validation
- `tests/test_magentic_fleet.py` - 14 core orchestration scenarios
- `tests/test_mem0_context_provider.py` - Memory integration
- Mock `OpenAIResponsesClient` to avoid API costs in tests

### Running Specific Tests

```bash
# Run specific test
uv run pytest tests/test_config.py::test_orchestrator_agent -v

# Run with filter
uv run pytest tests/test_magentic_fleet.py -k "test_orchestrator"

# Run end-to-end tests (requires dev server)
make test-e2e

# Run configuration validation only
make test-config

# Run tests for specific agent
uv run pytest tests/agents/coder/test_code_interpreter_tool.py -v
```

## Human-in-the-Loop (HITL)

### Approval System

- Configuration: `workflow.yaml` → `human_in_the_loop.enabled`
- Core interfaces: `core/approval.py` (ApprovalRequest, ApprovalResponse)
- Tools requiring approval: code_execution, file_operations, external_api_calls
- Use `create_approval_request()` helper for approval flows

### Approval Handler Architecture

Abstract `ApprovalHandler` class enables multiple UI implementations:

```python
class ApprovalHandler(ABC):
    @abstractmethod
    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        pass
```

### Configuration-Driven Approval Policies

Approval requirements defined in `workflow.yaml`:

```yaml
human_in_the_loop:
  enabled: true
  approval_timeout_seconds: 300
  require_approval_for:
    - code_execution
    - file_operations
    - external_api_calls
  trusted_operations:
    - web_search
    - data_analysis
```

## State Persistence

### Checkpointing

- Reduces 50-80% retry costs by avoiding redundant LLM calls
- Configure in `workflow.yaml` under `checkpointing`
- Storage types: File (persistent) or InMemory (testing)
- Auto-resume: `resume_from_checkpoint=<id>` in `MagenticFleet.run()`

### Checkpoint Management Features

- **File-Based Storage**: Persistent state in `./var/checkpoints`
- **Metadata Storage**: Rich metadata with timestamps and agent states
- **Listing and Sorting**: `list_checkpoints()` with sorting capabilities
- **Cleanup Management**: Automatic cleanup after configured days

## Frontend Architecture

### Key Components

- `ChatContainer.tsx` - Main chat UI
- `useFastAPIChat.ts` - SSE streaming hook
- API proxy: Vite config routes `/api/*` to backend `:8000`

### Frontend Technology Stack

- **React 18.3+** with TypeScript for type safety
- **Vite 7.x** for fast development and optimized builds
- **shadcn/ui** component library with Radix UI primitives
- **Tailwind CSS** for utility-first styling
- **Zustand** for lightweight state management
- **TanStack Query** for server state management
- **React Hook Form** with Zod validation
- **Lucide React** for modern iconography
- **Framer Motion** for animations and transitions

### Frontend Development Commands

```bash
cd src/frontend
npm run dev        # Development server (port 5173)
npm run build      # Production build
npm run build:dev  # Development build
npm run lint       # ESLint
npm run lint:fix   # ESLint with auto-fix
npm run format     # Prettier formatting
npm run preview    # Preview production build
```

### Vite 7.x Migration Best Practices

**Completed October 2025**: Full migration from Vite 6.x to Vite 7.x with enhanced infrastructure

**Key Improvements:**
- **Build Performance**: 13% faster build times (3.79s vs 4.66s)
- **Hot Module Replacement**: Improved development experience with faster updates
- **Bundle Optimization**: Stable bundle size (871 MB / 273 MB gzipped) with better tree-shaking
- **Developer Tooling**: Enhanced error reporting and source map generation
- **TypeScript Integration**: Seamless integration with stricter type checking

**Frontend Hook Architecture (Post-Migration):**
- **useSSEConnection** (315 lines) - Robust SSE event streaming with memory management
- **useMessageState** (245 lines) - Message state management with delta batching optimization
- **useApprovalWorkflow** (290 lines) - HITL approval request handling with retry logic
- **useConversationHistory** (100 lines) - Conversation history loading with parsing
- **useFastAPIChat** (571 lines) - Main orchestrator hook with clear separation of concerns

**Frontend-Backend Wiring Enhancements:**
- **Explicit Conversation Creation**: Frontend now creates conversations via POST /v1/conversations
- **Robust SSE Parsing**: Event buffer accumulation handles multi-line JSON without crashes
- **Exponential Backoff Retry**: 3-attempt retry with 100ms→200ms→400ms backoff across 6 API operations
- **Health Check Integration**: Backend monitoring every 30s with exponential backoff when disconnected
- **API Path Helpers**: Consistent path generation for conversations and entities

## Production Readiness

### Type Safety Standards

- **100% mypy compliance** required across all code
- Use `Type | None` instead of `Optional[Type]`
- Explicit type annotations for all function parameters and returns
- Use `# type: ignore` sparingly with justification comments

### Code Quality Gates

All quality checks must pass before commits:

```bash
make check          # Lint + format + type-check (all must pass)
make test-config    # Configuration validation (6/6 tests must pass)
make test           # Full test suite
make validate-agents  # Validate AGENTS.md documentation invariants
```

### Production Deployment Checklist

- ✅ All type errors resolved (current: 0 errors across 83 files)
- ✅ Configuration validation passes
- ✅ HITL approval system configured for sensitive operations
- ✅ Checkpointing enabled for cost optimization
- ✅ OpenTelemetry tracing configured
- ✅ Environment variables properly set
- ✅ Agent documentation invariants validated (`make validate-agents`)
- ✅ Vite 7.x migration complete with production-grade error handling
- ✅ Frontend-backend wiring robust with exponential backoff retry logic
- ✅ SSE event parsing handles complex multi-line JSON structures
- ✅ Hook-based frontend architecture with comprehensive test coverage

## Common Pitfalls to Avoid

❌ **Hardcoding models** - Always read from `agents/<role>/config.yaml`
❌ **Bypassing YAML config** - Move behavior to config, not Python code
❌ **Using `python` directly** - Always use `uv run` prefix
❌ **Skipping config validation** - Run `make test-config` after YAML changes
❌ **Tool schema mismatches** - Ensure Pydantic models match across codebase
❌ **Type safety violations** - Never commit with mypy errors
❌ **Missing HITL approvals** - Configure approval for code execution, file ops

✅ **Before committing** - Run `make check`, `make test-config`, `make test`
✅ **Type safety first** - Fix all mypy errors before PR
✅ **Configuration validation** - Always validate after YAML changes
✅ **Defensive programming** - Use proper type guards and error handling

## Key Architectural Strengths

1. **Configuration-Driven**: YAML-first approach enables runtime flexibility
2. **Type Safety**: 100% mypy compliance with strict typing
3. **Event-Driven**: Real-time streaming and observability
4. **Modular Design**: Clear separation between orchestration, agents, and tools
5. **Production Ready**: Comprehensive error handling, logging, and monitoring
6. **Cost Optimized**: Intelligent checkpointing and model selection
7. **Security conscious**: HITL approval system and audit logging

## Design Patterns Employed

- **Builder Pattern**: `FleetBuilder` for workflow construction
- **Factory Pattern**: Agent factories with configuration injection
- **Observer Pattern**: Event-driven callbacks and observability
- **Strategy Pattern**: Dynamic agent spawning based on task analysis
- **Template Method**: Consistent agent creation workflow
- **Command Pattern**: Approval request/response system

## Recent v0.5.4 Improvements

### Modular Architecture Patterns

- **Planner-Executor-Verifier-Generator**: Complete modular workflow system
- **Workflow as Agent**: Reflection and retry pattern with Worker/Reviewer agents
- **Type Safety**: 100% mypy compliance with strict typing enforcement
- **Production Patterns**: Error handling, logging, and observability best practices

### New Development Workflows

```bash
# Validate everything before development
make test-config && make check

# Development with type safety
uv run python -m agenticfleet  # Always use uv run

# Test specific components
uv run pytest tests/test_magentic_fleet.py -k "test_orchestrator"

# HITL approval demo
make demo-hitl

# Clean development environment
make clean

# Setup pre-commit hooks
make pre-commit-install
```

### Performance Optimizations

- **Checkpointing**: 50-80% cost reduction on retries
- **Streaming**: Real-time SSE responses for better UX
- **Caching**: Intelligent response caching where appropriate
- **Resource Management**: Proper cleanup and resource disposal

## File Structure Reference

### Backend Core

- `src/agenticfleet/workflow.py` - Workflow factories and event handlers
- `src/agenticfleet/server.py` - FastAPI server with SSE streaming
- `src/agenticfleet/api/` - API models and event translation
- `src/agenticfleet/core/` - Core types and utilities

### Frontend Core

- `src/frontend/src/lib/use-fastapi-chat.ts` - SSE integration hook
- `src/frontend/src/components/ChatContainer.tsx` - Main chat UI
- `src/frontend/vite.config.ts` - Vite 7.x build configuration

### Configuration

- [`src/agenticfleet/magentic_fleet.yaml`](src/agenticfleet/magentic_fleet.yaml) - YAML workflow definitions
- [`pyproject.toml`](pyproject.toml) - Python dependencies and Microsoft Agent Framework integration
- [`src/frontend/package.json`](src/frontend/package.json) - Frontend dependencies with Vite 7.x
- [`.mcp.json`](.mcp.json) - Model Context Protocol server configurations
- [`Makefile`](Makefile) - Development commands and build automation
