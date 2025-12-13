<p align="center">
  <img src="assets/banner.png" alt="AgenticFleet" width="100%"/>
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"/></a>
  <a href="https://pepy.tech/projects/agentic-fleet"><img src="https://static.pepy.tech/personalized-badge/agentic-fleet?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BLUE&left_text=downloads" alt="PyPI Downloads"/></a>
  <a href="https://deepwiki.com/qredence/agentic-fleet"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"/></a>
  <a href="https://pypi.org/project/agentic-fleet/"><img src="https://img.shields.io/pypi/v/agentic-fleet?color=blue" alt="PyPI Version"/></a>
  <a href="https://pypi.org/project/agentic-fleet/"><img src="https://img.shields.io/pypi/pyversions/agentic-fleet" alt="Python Versions"/></a>
</p>

<h3 align="center">
  <b>Self-Optimizing Multi-Agent Orchestration</b>
</h3>

<p align="center">
  Intelligent task routing with <a href="https://github.com/stanfordnlp/dspy">DSPy</a> • Robust execution with <a href="https://github.com/microsoft/agent-framework">Microsoft Agent Framework</a>
</p>

---

## ✨ What is AgenticFleet?

AgenticFleet is a production-ready multi-agent orchestration system that **automatically routes tasks to specialized AI agents** and orchestrates their execution through a self-optimizing pipeline.

```
User Task → Analysis → Intelligent Routing → Agent Execution → Quality Check → Output
```

**Key Features:**

- 🧠 **DSPy-Powered Routing** – Typed signatures with Pydantic validation for reliable structured outputs
- 🔄 **6 Execution Modes** – Auto, Delegated, Sequential, Parallel, Handoff, and Discussion
- 🎯 **9+ Specialized Agents** – Researcher, Analyst, Writer, Reviewer, Coder, Planner, Executor, Verifier, Generator
- ⚡ **Smart Fast-Path** – Simple queries bypass multi-agent routing (<1s response)
- 🧍 **Human-in-the-Loop (HITL)** – Request/response events can pause execution until the user responds
- ♻️ **Checkpoint Resume** – Resume interrupted runs using agent-framework checkpoint semantics (message XOR checkpoint_id)
- 📊 **Built-in Evaluation** – Azure AI Evaluation integration for quality metrics
- 🔍 **OpenTelemetry Tracing** – Full observability with Azure Monitor export

## 🚀 Quick Start

### Installation

```bash
# Clone and install
git clone https://github.com/Qredence/agentic-fleet.git && cd agentic-fleet
uv sync  # or: pip install agentic-fleet

# Configure environment
cp .env.example .env
# Set OPENAI_API_KEY (required)
# Set TAVILY_API_KEY (optional, enables web search)
```

### Run

```bash
# Interactive CLI
agentic-fleet

# Single task
agentic-fleet run -m "Research the latest advances in AI agents" --verbose

# Development server (backend + frontend)
agentic-fleet dev
```

## 📖 Usage

### CLI

```bash
agentic-fleet                              # Interactive console
agentic-fleet run -m "Your task"           # Execute a task
agentic-fleet run -m "Query" --mode handoff  # Specific execution mode
agentic-fleet list-agents                  # Show available agents
agentic-fleet dev                          # Start dev servers
```

### Python API

```python
import asyncio
from agentic_fleet.workflows import create_supervisor_workflow

async def main():
    workflow = await create_supervisor_workflow()
    result = await workflow.run("Summarize the transformer architecture")
    print(result["result"])

asyncio.run(main())
```

### Web Interface

```bash
agentic-fleet dev  # Backend: http://localhost:8000, Frontend: http://localhost:5173
```

The web interface provides:

- Real-time streaming responses with workflow visualization
- Conversation history with persistence
- Agent activity display and orchestration insights

Notes:

- The **fast-path** is intended for first-turn/simple prompts; follow-up turns in an existing conversation are routed through the full workflow so history is respected.
- For advanced streaming semantics (HITL responses and checkpoint resume), see the [Frontend Guide](docs/users/frontend.md#websocket-protocol).

## 🤖 Agents & Execution Modes

### Specialized Agents

| Agent          | Expertise                                           |
| -------------- | --------------------------------------------------- |
| **Researcher** | Web search, information gathering, source synthesis |
| **Analyst**    | Data analysis, code review, technical evaluation    |
| **Writer**     | Content creation, documentation, summarization      |
| **Reviewer**   | Quality assurance, fact-checking, critique          |
| **Coder**      | Code generation, debugging, implementation          |
| **Planner**    | Task decomposition, strategy, coordination          |
| **Executor**   | Task execution and action coordination              |
| **Verifier**   | Output validation and correctness checking          |
| **Generator**  | Creative content and ideation                       |

### Execution Modes

| Mode           | Description                         | Best For             |
| -------------- | ----------------------------------- | -------------------- |
| **Auto**       | DSPy selects optimal mode (default) | Most tasks           |
| **Delegated**  | Single agent handles entire task    | Focused work         |
| **Sequential** | Agents work in pipeline             | Multi-step tasks     |
| **Parallel**   | Concurrent agent execution          | Independent subtasks |
| **Handoff**    | Direct agent-to-agent transfers     | Specialized chains   |
| **Discussion** | Multi-agent group chat              | Complex problems     |

## ⚙️ Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
TAVILY_API_KEY=tvly-...              # Web search capability
DSPY_COMPILE=true                    # Enable DSPy optimization
ENABLE_OTEL=true                     # OpenTelemetry tracing
OTLP_ENDPOINT=http://...             # Tracing endpoint
ENABLE_SENSITIVE_DATA=true           # Capture prompts in traces/telemetry (default: false)
AGENTICFLEET_USE_COSMOS=true         # Enable Azure Cosmos DB integration
AGENTICFLEET_DEFAULT_USER_ID=user123 # Default user ID for multi-tenant scoping
```

### Workflow Configuration

All runtime settings are in `src/agentic_fleet/config/workflow_config.yaml`:

```yaml
dspy:
  model: gpt-5.2 # Primary model for DSPy tasks
  routing_model: grok-4-fast # Fast model for routing decisions
  use_typed_signatures: true # Pydantic-validated outputs
  enable_routing_cache: true # Cache routing decisions
  routing_cache_ttl_seconds: 300 # Cache TTL (5 minutes)

workflow:
  supervisor:
    max_rounds: 15
    enable_streaming: true
  quality:
    refinement_threshold: 8.0
    enable_refinement: false # Disabled for speed

agents:
  researcher:
    model: gpt-4.1-mini
    tools: [TavilySearchTool]
  coder:
    model: gpt-5.1-codex-mini
    tools: [HostedCodeInterpreterTool]
```

## 🏗️ Architecture

```
src/agentic_fleet/
├── agents/           # Agent definitions & AgentFactory
├── api/              # FastAPI backend, routes, SSE streaming, middleware
├── cli/              # Typer CLI commands
├── config/           # workflow_config.yaml (source of truth)
├── core/             # Core abstractions and base classes
├── data/             # Training examples, evaluation datasets
├── dspy_modules/     # DSPy signatures, typed models, assertions
├── evaluation/       # Azure AI Evaluation integration
├── models/           # Pydantic models and schemas
├── services/         # Business logic services
├── tools/            # Tavily, browser, MCP bridges, code interpreter
├── utils/            # Helpers, caching, tracing, Cosmos DB
└── workflows/        # Orchestration: supervisor, executors, strategies

src/frontend/         # React 19 + Vite + Tailwind UI
```

**Key Design Principles:**

1. **Config-Driven** – All models, agents, and thresholds in YAML
2. **Offline Compilation** – DSPy modules compiled offline, never at runtime
3. **Type Safety** – Pydantic models for all DSPy outputs
4. **Assertion-Driven** – DSPy assertions for routing validation

## 🧪 Development

```bash
make install           # Install dependencies
make dev               # Run backend + frontend
make test              # Run tests
make check             # Lint + type-check (run before committing)
make clear-cache       # Clear DSPy cache after module changes
```

## 📚 Documentation

| Guide                                                               | Description                     |
| ------------------------------------------------------------------- | ------------------------------- |
| [Getting Started](docs/users/getting-started.md)                    | Installation and first steps    |
| [Configuration](docs/users/configuration.md)                        | Environment and workflow config |
| [Frontend Guide](docs/users/frontend.md)                            | Web interface usage             |
| [Architecture](docs/developers/architecture.md)                     | System design and internals     |
| [DSPy Integration](docs/guides/dspy-agent-framework-integration.md) | DSPy + Agent Framework patterns |
| [Tracing](docs/guides/tracing.md)                                   | OpenTelemetry setup             |
| [Troubleshooting](docs/users/troubleshooting.md)                    | Common issues and solutions     |

## 🆕 What's New in v0.6.95

- **Secure-by-Default Tracing** – `capture_sensitive` now defaults to `false` everywhere (schema, YAML, built-in defaults)
- **Cosmos DB Partition-Key Fixes** – `query_agent_memory()` uses single-partition queries; history loads are user-scoped when `userId` is available
- **Cache Telemetry Redaction** – Task previews are redacted by default; opt-in via `ENABLE_SENSITIVE_DATA=true`
- **Typed DSPy Signatures** – Pydantic models for validated, type-safe outputs
- **DSPy Assertions** – Hard constraints and soft suggestions for routing validation
- **Routing Cache** – TTL-based caching for routing decisions

See [CHANGELOG.md](CHANGELOG.md) for full release history.

## 🤝 Contributing

We welcome contributions! Here's how to get started:

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/agentic-fleet.git
cd agentic-fleet

# Install dev dependencies
uv sync

# Create a branch
git checkout -b feature/your-feature-name

# Make changes, then run checks
make check              # Lint + type-check
make test               # Run tests

# Submit a PR
```

**Guidelines:**

- Follow the existing code style (Ruff formatting, type hints)
- Add tests for new features
- Update documentation as needed
- Use [conventional commits](https://www.conventionalcommits.org/) (optional but appreciated)

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the **MIT License** – you're free to use, modify, and distribute this software for any purpose.

See the [LICENSE](LICENSE) file for the full text.

## 🙏 Acknowledgments

AgenticFleet stands on the shoulders of giants. Special thanks to:

| Project                                                                   | Contribution                                   |
| ------------------------------------------------------------------------- | ---------------------------------------------- |
| [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | Multi-agent runtime and orchestration patterns |
| [DSPy](https://github.com/stanfordnlp/dspy)                               | Programmatic LLM pipelines and optimization    |
| [Tavily](https://tavily.com)                                              | AI-native search API for research agents       |
| [FastAPI](https://fastapi.tiangolo.com/)                                  | Modern async Python web framework              |
| [Pydantic](https://docs.pydantic.dev/)                                    | Data validation and settings management        |
| [OpenTelemetry](https://opentelemetry.io/)                                | Observability and distributed tracing          |

And to all our [contributors](https://github.com/Qredence/agentic-fleet/graphs/contributors) who help make AgenticFleet better! 💜

---

<p align="center">
  <a href="https://github.com/Qredence/agentic-fleet/issues/new?template=bug_report.md">🐛 Report Bug</a> •
  <a href="https://github.com/Qredence/agentic-fleet/issues/new?template=feature_request.md">✨ Request Feature</a> •
  <a href="https://github.com/Qredence/agentic-fleet/discussions">💬 Discussions</a>
</p>

<p align="center">
  <sub>Made with ❤️ by <a href="https://qredence.ai">Qredence</a></sub>
</p>
