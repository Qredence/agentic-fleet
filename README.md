# AgenticFleet - Phase 1

A sophisticated multi-agent system powered by Microsoft Agent Framework that coordinates specialized AI agents to solve complex tasks through dynamic delegation and collaboration.

## 🎯 Overview

AgenticFleet implements a custom orchestration pattern where an orchestrator agent intelligently delegates tasks to specialized agents:

- **🎯 Orchestrator Agent**: Plans and coordinates task distribution
- **🔍 Researcher Agent**: Gathers information through web searches
- **💻 Coder Agent**: Writes and executes Python code
- **📊 Analyst Agent**: Analyzes data and suggests visualizations

## ✨ Features

- ✅ **Dynamic Task Decomposition**: Automatic breakdown of complex tasks
- ✅ **Multi-Agent Coordination**: Seamless collaboration between specialized agents
- ✅ **Event-Driven Architecture**: Real-time monitoring and observability
- ✅ **Structured Responses**: Type-safe tool outputs with Pydantic models
- ✅ **Configurable Execution**: Safety controls and execution limits
- ✅ **Individual Agent Configs**: Dedicated configuration per agent
- ✅ **Persistent Memory**: `mem0` integration for long-term memory

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         User Interface (REPL)           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Custom Workflow Orchestrator       │
│   (Coordination & State Management)     │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────────┐    ┌──────────────┐
│Orchestrator │◄───┤ Specialized  │
│   Agent     │    │    Agents    │
└─────┬───────┘    └──────┬───────┘
      │                   │
      │  ┌────────────────┼────────┐
      │  │                │        │
      ▼  ▼                ▼        ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│Researcher│  │  Coder   │  │ Analyst  │
│(Web)     │  │(Code)    │  │(Data)    │
└──────────┘  └──────────┘  └──────────┘
      ▲
      │
┌─────┴───────┐
│ Mem0 Context│
│  Provider   │
└─────────────┘
```

## 📋 Prerequisites

- **Python**: 3.12 or higher
- **Azure AI Project**: An Azure AI project with a deployed model.
- **Azure AI Search**: An Azure AI Search service.
- **uv**: Modern Python package manager (recommended)

## 🚀 Quick Start

### 1. Clone and Navigate

```bash
cd AgenticFleet
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your keys and endpoints
```

### 3. Install Dependencies (uv-first)

```bash
# Sync (creates .venv automatically if missing)
uv sync

# Optional: activate shell (not required when using `uv run`)
source .venv/bin/activate  # macOS/Linux
```

If you must use pip (not recommended), see docs/QUICK_REFERENCE.md.

### 4. Run the Application

```bash
uv run python tests/test_config.py   # Fast config validation (should pass 6/6)
uv run python main.py                # Launch workflow REPL
```

### 5. Developer Workflow

**Using Makefile (recommended):**

```bash
make help          # Show all available commands
make install       # First-time setup
make test-config   # Validate configuration (6/6 tests)
make run           # Launch application
make check         # Run all quality checks (lint + type-check)
make format        # Auto-format code
```

**Using uv directly:**

```bash
# Format & lint
uv run ruff check .
uv run black .

# Type checking
uv run mypy .

# Tests
uv run pytest -q

# All-in-one validation
uv sync && uv run ruff check . && uv run mypy . && uv run pytest -q
```

**Pre-commit hooks** (automated checks on git commit):

```bash
make pre-commit-install
# or: uv run pre-commit install
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# Azure AI Project Endpoint
AZURE_AI_PROJECT_ENDPOINT=your-azure-ai-project-endpoint

# Azure AI Search Configuration
AZURE_AI_SEARCH_ENDPOINT=your-azure-ai-search-endpoint
AZURE_AI_SEARCH_KEY=your-azure-ai-search-key

# Azure OpenAI Deployed Model Names
AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME=your-chat-completion-model-name
AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME=your-embedding-model-name

# Log Level (e.g., INFO, DEBUG)
LOG_LEVEL=INFO
```

## 📖 Documentation

All documentation is located in the `docs/` folder:

- **[Mem0 Integration](docs/MEM0_INTEGRATION.md)** - How `mem0` is integrated for persistent memory.
- **[Progress Tracker](docs/ProgressTracker.md)** - Project status and milestones
- **[Phase 1 PRD](docs/af-phase-1.md)** - Original product requirements
- **[Repository Guidelines](docs/AGENTS.md)** - Development rules and conventions
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Getting started guide
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - Technical details
- **[Migration Guide](docs/MIGRATION_TO_RESPONSES_API.md)** - OpenAI API updates
- **[Bug Fixes](docs/FIXES.md)** - Issue resolutions and fixes

## 🛠️ Development Tools

- **uv**: Fast Python package manager with lockfile support
- **Ruff**: Lightning-fast linter and formatter
- **Black**: Opinionated code formatter
- **mypy**: Static type checker
- **pytest**: Testing framework
- **pre-commit**: Git hooks for automated quality checks
- **GitHub Actions**: CI/CD with automated testing and linting
- **Makefile**: Convenient command shortcuts

## 🔄 CI/CD

The project includes automated CI/CD via GitHub Actions (`.github/workflows/ci.yml`):

- ✅ Lint with Ruff
- ✅ Format check with Black
- ✅ Type check with mypy
- ✅ Configuration validation
- ✅ Test suite execution
- ✅ Security scanning (optional)
- ✅ Matrix testing (Python 3.12 & 3.13)
- ✅ Automated dependency caching

Pre-commit.ci integration provides automatic fixes on pull requests.
