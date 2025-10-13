# AgenticFleet

[![CI](https://github.com/Qredence/AgenticFleet/workflows/CI/badge.svg)](https://github.com/Qredence/AgenticFleet/actions/workflows/ci.yml)
[![Release](https://github.com/Qredence/AgenticFleet/workflows/Release/badge.svg)](https://github.com/Qredence/AgenticFleet/actions/workflows/release.yml)
[![CodeQL](https://github.com/Qredence/AgenticFleet/workflows/CodeQL%20Security%20Analysis/badge.svg)](https://github.com/Qredence/AgenticFleet/actions/workflows/codeql.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/agentic-fleet?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=MAGENTA&left_text=downloads)](https://pepy.tech/projects/agentic-fleet)

**Version:** 0.5.0
**Package:** `agentic-fleet` (PyPI) | `agenticfleet` (import)

A sophisticated multi-agent system powered by Microsoft Agent Framework that coordinates specialized AI agents to solve complex tasks through dynamic delegation and collaboration.

## 🎯 Overview

AgenticFleet implements a custom orchestration pattern where an orchestrator agent intelligently delegates tasks to specialized agents:

- **🎯 Orchestrator Agent**: Plans and coordinates task distribution
- **🔍 Researcher Agent**: Gathers information through web searches
- **💻 Coder Agent**: Writes and executes Python code
- **📊 Analyst Agent**: Analyzes data and suggests visualizations

## ✨ Features

- ✅ **Modern Package Structure**: PyPA-recommended `src/` layout for import safety
- ✅ **Dynamic Task Decomposition**: Automatic breakdown of complex tasks
- ✅ **Multi-Agent Coordination**: Seamless collaboration between specialized agents
- ✅ **Event-Driven Architecture**: Real-time monitoring and observability
- ✅ **Structured Responses**: Type-safe tool outputs with Pydantic models
- ✅ **Configurable Execution**: Safety controls and execution limits
- ✅ **Individual Agent Configs**: Dedicated configuration per agent
- ✅ **Persistent Memory**: `mem0` integration for long-term memory
- ✅ **Console Script**: Easy CLI access via `agentic-fleet` command

## 🏗️ Architecture

```text
┌─────────────────────────────────────────┐
│         User Interface (CLI)            │
│     Console: agentic-fleet              │
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

### Package Structure (src/ Layout)

```text
src/agenticfleet/           # Main package (import: agenticfleet)
├── __init__.py            # Package entry, version, exports
├── __main__.py            # Module entry (python -m agenticfleet)
├── agents/                # All agent factories + tools
│   ├── orchestrator/      # Orchestrator agent
│   │   ├── agent.py       # Factory: create_orchestrator_agent()
│   │   ├── config.yaml    # Agent-specific configuration
│   │   └── tools/         # Agent tools (if any)
│   ├── researcher/        # Researcher agent with web search
│   │   ├── agent.py       # Factory: create_researcher_agent()
│   │   ├── config.yaml
│   │   └── tools/
│   │       └── web_search_tools.py
│   ├── coder/             # Coder agent with code execution
│   │   ├── agent.py       # Factory: create_coder_agent()
│   │   ├── config.yaml
│   │   └── tools/
│   │       └── code_interpreter.py
│   └── analyst/           # Analyst agent with data analysis
│       ├── agent.py       # Factory: create_analyst_agent()
│       ├── config.yaml
│       └── tools/
│           └── data_analysis_tools.py
├── workflows/             # Multi-agent orchestration
│   └── multi_agent.py     # MultiAgentWorkflow class
├── config/                # Configuration management
│   ├── settings.py        # Settings class (loads env vars)
│   └── workflow.yaml      # Workflow-level config
├── context/               # Long-term memory providers
│   └── mem0_provider.py   # Mem0 integration
├── core/                  # Core utilities
│   ├── exceptions.py      # Custom exceptions
│   ├── logging.py         # Logging configuration
│   └── types.py           # Type definitions, enums
└── cli/                   # CLI interface
    └── repl.py            # Interactive REPL

tests/                     # All tests
├── test_config.py         # Configuration validation
├── test_mem0_context_provider.py  # Memory tests
└── test_hello.py          # Sanity check

docs/                      # Documentation
├── AGENTS.md              # Agent catalog & orchestration guide
├── MEM0_INTEGRATION.md    # Memory integration docs
├── MIGRATION_COMPLETE.md  # Migration report
├── TEMPERATURE_FIX.md     # API compliance fixes
├── COMMANDS.md            # Command reference
└── ...
```

## 📋 Prerequisites

- **Python**: 3.12 or higher
- **Azure AI Project**: An Azure AI project with a deployed model.
- **Azure AI Search**: An Azure AI Search service.
- **uv**: Modern Python package manager (recommended)

## 🚀 Quick Start

### 1. Clone and Navigate

```bash
git clone https://github.com/Qredence/AgenticFleet.git
cd AgenticFleet
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your keys and endpoints
# Required:
#   - OPENAI_API_KEY
#   - AZURE_AI_PROJECT_ENDPOINT
#   - AZURE_AI_SEARCH_ENDPOINT
#   - AZURE_AI_SEARCH_KEY
#   - AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME
#   - AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME
```

### 3. Install Dependencies (uv-first approach)

**Using uv (recommended):**

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates .venv automatically)
uv sync

# Optional: activate shell (not required when using `uv run`)
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

#### Using pip (not recommended)

See `docs/getting-started/command-reference.md` for pip-based installation.

### 4. Validate Configuration

```bash
# Run configuration tests (should pass 6/6)
uv run pytest tests/test_config.py -v
```

### 5. Run the Application

#### Method 1: Console script (easiest)

```bash
uv run agentic-fleet
```

#### Method 2: Module execution

```bash
uv run python -m agenticfleet
```

#### Method 3: Direct REPL file (legacy)

```bash
uv run python src/agenticfleet/cli/repl.py
```

### 5. Developer Workflow

#### Using Makefile (recommended)

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
# Format code
uv run black .

# Lint code
uv run ruff check .
uv run ruff check --fix .    # Auto-fix issues

# Type checking
uv run mypy src/agenticfleet

# Run tests
uv run pytest                # All tests
uv run pytest -v             # Verbose
uv run pytest tests/test_config.py  # Specific file

# All-in-one validation
uv sync && uv run black . && uv run ruff check . && uv run mypy src/agenticfleet && uv run pytest
```

**Pre-commit hooks** (automated checks on git commit):

```bash
make pre-commit-install
# or: uv run pre-commit install
```

## 💡 Usage Examples

### Basic Import

```python
# Import package version
from agenticfleet import __version__
print(f"AgenticFleet v{__version__}")

# Import workflow
from agenticfleet.workflows import workflow

# Run a task
result = await workflow.run("Research Python best practices")
```

### Creating Individual Agents

```python
from agenticfleet.agents import (
    create_orchestrator_agent,
    create_researcher_agent,
    create_coder_agent,
    create_analyst_agent,
)

# Create agents
orchestrator = create_orchestrator_agent()
researcher = create_researcher_agent()
coder = create_coder_agent()
analyst = create_analyst_agent()

# Use individual agent
result = await researcher.run("Search for Python ML libraries")
```

### Using Configuration

```python
from agenticfleet.config import settings

# Access settings
api_key = settings.openai_api_key
model = settings.openai_model

# Load agent-specific config
agent_cfg = settings.load_agent_config("orchestrator")
print(agent_cfg["agent"]["name"])  # "orchestrator"
```

### Custom Workflow

```python
from agenticfleet.workflows import MultiAgentWorkflow

# Create workflow instance
workflow = MultiAgentWorkflow()

# Run task with automatic agent coordination
result = await workflow.run(
    "Analyze sales data and create visualizations"
)
print(result)
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

All documentation lives in `docs/` and is organised by topic:

- [AGENTS.md](docs/AGENTS.md) – end-to-end guide to every agent, workflows, tools, and extension patterns.
- `getting-started/`
  - [quick-reference](docs/getting-started/quick-reference.md) – one-page onboarding.
  - [command-reference](docs/getting-started/command-reference.md) – uv + Makefile cheat sheet.
- `overview/`
  - [implementation-summary](docs/overview/implementation-summary.md) – architecture deep dive.
  - [progress-tracker](docs/overview/progress-tracker.md) – milestone and roadmap log.
- `operations/`
  - [repository-guidelines](docs/operations/repository-guidelines.md) – coding standards.
  - [developer-environment](docs/operations/developer-environment.md) – uv workflows, VS Code tasks, CI gates.
  - [github-actions-setup](docs/operations/github-actions-setup.md) & [workflows-overview](docs/operations/github-workflows-overview.md) – automation reference.
  - [mem0-integration](docs/operations/mem0-integration.md) – persistent memory configuration.
  - [pypi-environment-setup](docs/operations/pypi-environment-setup.md) – trusted publishing checklist.
- `migrations/`
  - [responses-api-migration](docs/migrations/responses-api-migration.md).
  - [src-layout-migration](docs/migrations/src-layout-migration.md).
- `runbooks/`
  - [troubleshooting](docs/runbooks/troubleshooting.md) – recurring fixes (tag rules, ChatAgent params, mem0 tests).
- `releases/`
  - [2025-10-12-v0.5.0](docs/releases/2025-10-12-v0.5.0.md).
- `archive/`
  - Historical clean-up checklists and `.github` remediation summaries retained for audit.

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
- ✅ Configuration validation (6 tests)
- ✅ Full test suite execution (28 tests)
- ✅ Security scanning (optional)
- ✅ Matrix testing (Python 3.12 & 3.13)
- ✅ Automated dependency caching
- ✅ Pre-commit.ci integration for automatic fixes

## 🚢 Installation (Future PyPI)

Once published to PyPI, users can install AgenticFleet:

```bash
# Using pip
pip install agentic-fleet

# Using uv (recommended)
uv pip install agentic-fleet
```

Then import and use:

```python
from agenticfleet import __version__, MultiAgentWorkflow

print(f"AgenticFleet v{__version__}")

workflow = MultiAgentWorkflow()
result = await workflow.run("Your task here")
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the coding standards
4. Run tests: `uv run pytest`
5. Run quality checks: `make check` or `uv run black . && uv run ruff check . && uv run mypy src/agenticfleet`
6. Commit your changes (`git commit -m 'feat: add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Microsoft Agent Framework** - Core agent orchestration framework
- **OpenAI** - Language model APIs
- **mem0** - Persistent memory management
- **uv** - Fast Python package manager
- **Ruff** - Lightning-fast linter and formatter

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Qredence/AgenticFleet/issues)
- **Documentation**: [docs/](docs/)
- **Email**: <contact@qredence.ai>

---

### Built with ❤️ by Qredence
