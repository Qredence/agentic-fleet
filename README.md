![AgenticFleet](assets/banner.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/agentic-fleet?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BLUE&left_text=downloads)](https://pepy.tech/projects/agentic-fleet)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/qredence/agentic-fleet)

# AgenticFleet

A self-optimizing multi-agent orchestration system combining **DSPy** for intelligent task routing with **Microsoft agent-framework** for robust execution.

> **Note**: APIs may change between minor versions. Pin a version for production.

## Quick Start

```bash
# Install
git clone https://github.com/Qredence/agentic-fleet.git && cd agentic-fleet
uv sync  # or: pip install agentic-fleet

# Configure
cp .env.example .env
# Edit .env: set OPENAI_API_KEY (required), TAVILY_API_KEY (optional for web search)

# Run
agentic-fleet run -m "Research the latest AI advances" --verbose
```

## What It Does

AgenticFleet routes tasks to specialized AI agents and orchestrates their execution:

```
Task --> Analysis --> Routing --> Agent Execution --> Quality Check --> Output
```

**Agents**: Researcher (web search), Analyst (data/code), Writer, Reviewer, Coder, Planner

**Execution Modes**:
| Mode | Description |
|------|-------------|
| Auto | DSPy picks best mode (default) |
| Delegated | Single agent handles task |
| Sequential | Agents work in pipeline |
| Parallel | Concurrent execution |
| Handoff | Direct agent-to-agent transfers |
| Discussion | Multi-agent group chat |

## Usage

### CLI

```bash
agentic-fleet                                    # Interactive console
agentic-fleet run -m "Your task" --verbose       # Single task
agentic-fleet run -m "Query" --mode handoff      # Specific mode
agentic-fleet list-agents                        # Show available agents
```

### Python API

```python
import asyncio
from agentic_fleet.workflows import create_supervisor_workflow

async def main():
    workflow = await create_supervisor_workflow()
    result = await workflow.run("Summarize transformer architecture")
    print(result["result"])

asyncio.run(main())
```

### Backend API

```bash
./scripts/start_backend.sh  # http://localhost:8000
# Docs: http://localhost:8000/api/docs
```

## Configuration

**Environment** (`.env`):

```bash
OPENAI_API_KEY=sk-...          # Required
TAVILY_API_KEY=tvly-...        # Optional: web search
DSPY_COMPILE=true              # DSPy optimization
```

**Workflow** (`src/agentic_fleet/config/workflow_config.yaml`):

- Models, temperatures, agent settings
- Execution thresholds and limits
- Tracing and evaluation options

## Project Structure

```
src/agentic_fleet/
  agents/        # Agent definitions
  workflows/     # Orchestration logic
  dspy_modules/  # DSPy signatures & reasoner
  tools/         # Tavily, browser, code interpreter
  cli/           # Typer CLI
  app/           # FastAPI backend
src/frontend/    # React UI (optional)
scripts/         # Utilities
docs/            # Documentation
```

## Development

```bash
make install           # Install dependencies
make dev               # Run backend + frontend
make test              # Run tests
make check             # Lint + type-check
```

## Documentation

- [Getting Started](docs/users/getting-started.md)
- [Configuration](docs/users/configuration.md)
- [Architecture](docs/developers/architecture.md)
- [Troubleshooting](docs/users/troubleshooting.md)

## License

MIT - see [LICENSE](LICENSE)

## Acknowledgments

Built with [Microsoft agent-framework](https://github.com/microsoft/agent-framework), [DSPy](https://github.com/stanfordnlp/dspy), and [Tavily](https://tavily.com)
