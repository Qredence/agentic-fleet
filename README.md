# AgenticFleet - Phase 1

# 🤖 AgenticFleet - Phase 1

A sophisticated multi-agent system powered by Microsoft Agent Framework that coordinates specialized AI agents to solve complex tasks through dynamic delegation and collaboration.

## 🎯 Overview

AgenticFleet implements a **Magentic workflow pattern** where an orchestrator agent intelligently delegates tasks to specialized agents:

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

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         User Interface (REPL)           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Magentic Workflow Manager          │
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
```

## 📋 Prerequisites

- **Python**: 3.13.2 or higher
- **OpenAI API Key**: Required for agent interactions
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

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
```

### 3. Install Dependencies

Using **uv** (recommended):

```bash
# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

Using **pip**:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 4. Test Configuration

```bash
# Run configuration tests
python test_config.py
```

Expected output:

```
✓ PASS - Environment file
✓ PASS - OpenAI API Key
✓ PASS - Workflow config: max_rounds
✓ PASS - orchestrator_agent config
...
Overall: 6/6 tests passed
```

### 5. Run the Application

```bash
python main.py
```

## 💡 Usage Examples

### Example 1: Research and Code

```
🎯 Your task: Research Python machine learning libraries and write example code

🔄 Processing...
[Orchestrator delegates to Researcher]
[Researcher uses web_search_tool]
[Orchestrator delegates to Coder]
[Coder writes example code with code_interpreter_tool]

✅ TASK COMPLETED!
```

### Example 2: Data Analysis

```
🎯 Your task: Analyze e-commerce trends and suggest visualizations

🔄 Processing...
[Orchestrator delegates to Researcher]
[Orchestrator delegates to Analyst]
[Analyst uses data_analysis_tool and visualization_suggestion_tool]

✅ TASK COMPLETED!
```

## 📁 Project Structure

```
AgenticFleet/
├── main.py                          # Application entry point
├── test_config.py                   # Configuration test suite
├── pyproject.toml                   # Project dependencies
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore rules
│
├── config/                          # Configuration management
│   ├── __init__.py                 # Package initialization
│   ├── settings.py                 # Settings loader
│   └── workflow_config.yaml        # Workflow parameters
│
├── agents/                          # Agent implementations
│   ├── __init__.py                 # Package exports
│   │
│   ├── orchestrator_agent/         # Task coordinator
│   │   ├── __init__.py
│   │   ├── agent.py                # Factory function
│   │   ├── agent_config.yaml       # Configuration
│   │   └── tools/                  # No tools (delegates)
│   │
│   ├── researcher_agent/           # Information gatherer
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── agent_config.yaml
│   │   └── tools/
│   │       ├── __init__.py
│   │       └── web_search_tools.py
│   │
│   ├── coder_agent/                # Code specialist
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── agent_config.yaml
│   │   └── tools/
│   │       ├── __init__.py
│   │       └── code_interpreter.py
│   │
│   └── analyst_agent/              # Data analyst
│       ├── __init__.py
│       ├── agent.py
│       ├── agent_config.yaml
│       └── tools/
│           ├── __init__.py
│           └── data_analysis_tools.py
│
├── workflows/                       # Workflow orchestration
│   ├── __init__.py
│   └── magentic_workflow.py        # Multi-agent coordination
│
├── tests/                           # Test suite
│   └── __init__.py
│
└── docs/                            # Documentation
    └── af-phase-1.md               # Phase 1 PRD
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional
OPENAI_MODEL=gpt-4o
LOG_LEVEL=INFO
```

### Workflow Configuration (config/workflow_config.yaml)

```yaml
max_rounds: 10          # Maximum conversation rounds
max_stalls: 3           # Maximum stalls before intervention
max_resets: 2           # Maximum workflow resets
timeout_seconds: 300    # Task timeout
```

### Agent Configuration (agents/*/agent_config.yaml)

Each agent has its own configuration file:

```yaml
name: "orchestrator_agent"
model: "gpt-4o"
temperature: 0.1        # Agent-specific temperature
max_tokens: 4000
tools: []               # Agent-specific tools
```

## 🛠️ Tools

### Web Search Tool (Researcher)

- **Function**: `web_search_tool(query: str)`
- **Returns**: `WebSearchResponse` with `SearchResult[]`
- **Phase 1**: Mock responses
- **Phase 2**: Real search API integration

### Code Interpreter Tool (Coder)

- **Function**: `code_interpreter_tool(code: str, language: str)`
- **Returns**: `CodeExecutionResult` with output and timing
- **Safety**: Restricted globals, no file system access
- **Supported**: Python only in Phase 1

### Data Analysis Tools (Analyst)

- **Function 1**: `data_analysis_tool(data: str)`
- **Returns**: `DataAnalysisResponse` with insights
- **Function 2**: `visualization_suggestion_tool(data_type: str)`
- **Returns**: `VisualizationSuggestion` with chart types

## 🧪 Testing

Run the configuration test suite:

```bash
python test_config.py
```

Tests include:

- ✅ Environment variable validation
- ✅ Configuration file loading
- ✅ Agent configuration verification
- ✅ Tool import checks
- ✅ Agent factory validation
- ✅ Workflow import verification

## 📊 Agent Coordination Flow

1. **User Input** → `main.py` REPL
2. **Workflow Creation** → `create_magentic_workflow()`
3. **Task Delegation** → Orchestrator analyzes task
4. **Agent Execution** → Specialized agents process subtasks
5. **Tool Usage** → Agents invoke tools for capabilities
6. **Result Synthesis** → Orchestrator combines outputs
7. **Response** → User receives final result

## 🔒 Safety & Limits

- **Code Execution**: Sandboxed with restricted globals
- **Max Rounds**: 10 (prevents infinite loops)
- **Max Stalls**: 3 (detects stuck workflows)
- **Timeouts**: 300 seconds per task
- **API Rate Limiting**: Handled by OpenAI client

## 🚧 Phase 1 Limitations

- **Mock Tools**: Web search and data analysis use mock data
- **Python Only**: Code interpreter supports Python only
- **No Persistence**: Results not saved between sessions
- **Single User**: No multi-user support
- **Local Only**: No remote deployment capabilities

## 🎯 Roadmap: Phase 2+

- [ ] Real API integrations (web search, data sources)
- [ ] Multi-language code execution (JavaScript, TypeScript)
- [ ] Persistent conversation history
- [ ] User authentication and multi-user support
- [ ] Advanced visualization generation
- [ ] Agent performance metrics
- [ ] Web UI interface
- [ ] Docker deployment
- [ ] Cloud hosting support

## 🐛 Troubleshooting

### Import Errors

```bash
# Reinstall dependencies
uv sync --force
# or
pip install -e . --force-reinstall
```

### API Key Issues

```bash
# Verify .env file
cat .env | grep OPENAI_API_KEY

# Test API key
python -c "from config.settings import settings; print(settings.openai_api_key[:10])"
```

### Configuration Errors

```bash
# Validate YAML files
python -c "import yaml; yaml.safe_load(open('config/workflow_config.yaml'))"

# Run full config test
python test_config.py
```

## 📖 Documentation

All documentation is located in the `docs/` folder:

- **[Progress Tracker](docs/ProgressTracker.md)** - Project status and milestones
- **[Phase 1 PRD](docs/af-phase-1.md)** - Original product requirements
- **[Repository Guidelines](docs/AGENTS.md)** - Development rules and conventions
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Getting started guide
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - Technical details
- **[Migration Guide](docs/MIGRATION_TO_RESPONSES_API.md)** - OpenAI API updates
- **[Bug Fixes](docs/FIXES.md)** - Issue resolutions and fixes

## 🤝 Contributing

This is currently a Phase 1 implementation for validation.
Contributions will be accepted starting in Phase 2.

## 📄 License

[Specify your license]

## 👨‍💻 Author

**Qredence**

- Framework: Microsoft Agent Framework v1.0.0b251007
- AI Model: OpenAI GPT-4o

---

**Built with ❤️ using Microsoft Agent Framework**

## Overview

AgenticFleet coordinates four specialized AI agents to solve complex tasks through dynamic delegation:

- **Orchestrator**: Plans and delegates tasks
- **Researcher**: Gathers information using web search
- **Coder**: Writes and executes code
- **Analyst**: Provides data insights and visualization suggestions

## Features

✅ Multi-agent coordination via Magentic workflow  
✅ Structured tool responses using Pydantic models  
✅ OpenAI Responses API integration  
✅ Modular agent organization  
✅ Type-safe tool implementations  
✅ Event streaming and observability  
✅ Individual agent configurations

## Requirements

- Python 3.12+
- OpenAI API key
- uv package manager

## Installation

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: pip install uv
```

### 2. Setup project

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the project
uv pip install -e .

# Or with dev dependencies
uv pip install -e ".[dev]"
```

### 3. Configure environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your OpenAI API key
# OPENAI_API_KEY=your_actual_api_key_here
```

## Usage

```bash
python main.py
```

### Example Tasks

- "Research Python machine learning libraries and write example code for data analysis"
- "Analyze e-commerce sales trends and suggest appropriate visualizations"
- "Help me understand web development best practices with code examples"

## Project Structure

```
agenticfleet/
├── agents/              # Individual agent implementations
│   ├── orchestrator_agent/
│   │   ├── agent.py
│   │   └── agent_config.yaml
│   ├── researcher_agent/
│   │   ├── agent.py
│   │   ├── agent_config.yaml
│   │   └── tools/
│   ├── coder_agent/
│   │   ├── agent.py
│   │   ├── agent_config.yaml
│   │   └── tools/
│   └── analyst_agent/
│       ├── agent.py
│       ├── agent_config.yaml
│       └── tools/
├── config/              # Application configuration
│   ├── settings.py
│   └── workflow_config.yaml
├── workflows/           # Multi-agent workflows
│   └── magentic_workflow.py
└── main.py             # Application entry point
```

## Configuration

### Workflow Configuration

Edit `config/workflow_config.yaml` to adjust workflow behavior:

```yaml
workflow:
  max_rounds: 10
  max_stalls: 3
  max_resets: 2
```

### Agent Configuration

Each agent has its own `agent_config.yaml` file in its directory:

- `agents/orchestrator_agent/agent_config.yaml`
- `agents/researcher_agent/agent_config.yaml`
- `agents/coder_agent/agent_config.yaml`
- `agents/analyst_agent/agent_config.yaml`

Modify these files to customize agent behavior, tools, and prompts.

## Development

### Run tests

```bash
pytest
```

### Code formatting

```bash
black .
ruff check .
```

### Type checking

```bash
mypy .
```

## Architecture

- **Framework**: Microsoft Agent Framework 1.0.0+
- **Workflow**: Magentic pattern with dynamic task delegation
- **LLM Integration**: OpenAI Responses API with structured outputs
- **Tools**: Type-safe Pydantic models for all tool responses

## License

Copyright © 2024 Qredence

## Support

For issues and questions, please refer to the documentation in `docs/`.
