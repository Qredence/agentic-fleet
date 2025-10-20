![AgenticFleet Architecture](docs/afleet-preview.png)

# AgenticFleet

<style>
  .button-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 16px;
  }

  .blend-pill {
    --pill-sheen: rgba(0, 0, 0, 0.9);
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 11px 28px;
    border-radius: 9999px;
    text-decoration: none;
    text-color: #000000;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    overflow: hidden;
    isolation: isolate;
    color: #ffffff;
    mix-blend-mode: difference;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    box-shadow: 0 14px 32px rgba(0, 0, 0, 0.18);
    z-index: 1;
  }

  .blend-pill::before {
    content: "";
    position: absolute;
    inset: -2px;
    border-radius: inherit;
    background: var(--pill-sheen);
    mix-blend-mode: difference;
    border: 1px solid rgba(255, 255, 255, 0.22);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
    transition: transform 0.35s ease, opacity 0.35s ease;
  }

  .blend-pill[data-variant="primary"] {
    --pill-sheen: rgba(255, 255, 255, 0.95);
  }

  .blend-pill[data-variant="discord"] {
    --pill-sheen: rgba(255, 255, 255, 0.88);
  }

  .blend-pill[data-variant="light"] {
    --pill-sheen: rgba(255, 255, 255, 0.78);
  }

  .blend-pill:hover {
    transform: translateY(-2px);
    box-shadow: 0 22px 44px rgba(0, 0, 0, 0.24);
  }

  .blend-pill:hover::before {
    transform: scale(1.06);
  }

  .blend-pill__value {
    position: relative;
    z-index: 1;
    color: #00000;
    mix-blend-mode: none;
    font-size: 15px;
    font-weight: 700;
  }
</style>
<div class="button-row">
  <a class="blend-pill" data-variant="primary" href="https://agenticfleet.com" target="_blank" rel="noopener noreferrer">
    <span class="blend-pill__label">Join Cloud beta</span>
  </a>
  <a class="blend-pill" data-variant="discord" href="https://discord.gg/agenticfleet" target="_blank" rel="noopener noreferrer">
    <span class="blend-pill__label">Discord</span>
  </a>
  <a class="blend-pill" data-variant="light" href="https://pepy.tech/projects/agentic-fleet" target="_blank" rel="noopener noreferrer" aria-label="PyPI downloads for agentic-fleet">
    PyPI downloads
    <span class="blend-pill__value" id="pypi-downloads">—</span>
  </a>
</div>

<script>
(async function(){
  function compactFR(n){
    const fmt=(x,d)=>x.toFixed(d).replace('.', ',');
    if(n>=1_000_000){const d=(n%1_000_000)>=100_000?1:0;return fmt(n/1_000_000,d)+'m';}
    if(n>=1_000){const d=(n%1_000)>=100?1:0;return fmt(n/1_000,d)+'k';}
    return String(n);
  }
  const el=document.getElementById('pypi-downloads');
  async function tryProxy(){
    try{
      const res = await fetch('/api/pepy?project=agentic-fleet',{cache:'no-store'});
      if(!res.ok) throw new Error('proxy not ok');
      const { total } = await res.json();
      if(typeof total==='number'){ el.textContent = compactFR(total); return true; }
    }catch(e){}
    return false;
  }
  async function tryPepyDirect(){
    try{
      const res = await fetch('https://api.pepy.tech/api/v2/projects/agentic-fleet',{
        headers:{'Accept':'application/json'}, cache:'no-store', mode:'cors'
      });
      if(!res.ok) throw new Error('pepy v2 not ok');
      const data = await res.json();
      const total = data.total_downloads || data.total || (data.downloads && (data.downloads.all_time||data.downloads.total));
      if(typeof total==='number'){ el.textContent = compactFR(total); return true; }
    }catch(e){}
    return false;
  }
  async function tryBadgeParse(){
    try{
      const url='https://static.pepy.tech/personalized-badge/agentic-fleet?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads';
      const res=await fetch(url,{cache:'no-store',mode:'cors'});
      if(!res.ok) throw new Error('badge not ok');
      const svg=await res.text();
      const matches=[...svg.matchAll(/>([\d.,]+)\s*([kKmM]?)/g)];
      if(!matches.length) throw new Error('no number');
      const [,numStr,suffix]=matches[matches.length-1];
      let n=parseFloat(numStr.replace(',','.'));
      if(/k/i.test(suffix)) n*=1_000; else if(/m/i.test(suffix)) n*=1_000_000;
      el.textContent=compactFR(Math.round(n));
      return true;
    }catch(e){}
    return false;
  }
  if(!(await tryProxy()) && !(await tryPepyDirect()) && !(await tryBadgeParse())){
    el.textContent='N/A';
  }
})();
</script>

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

> **⚠️ Active Development Notice**
> This project is under active development. Features, APIs, and workflows may change. We recommend pinning to specific versions for production use.

---

## AgenticFleet Overview

- 🖥️ **Interactive CLI** – Rich terminal interface for direct agent interaction
- 🌐 **Web Frontend** – Modern React UI wired to agent-as-workflow pattern (default)
- 📓 **Jupyter Notebooks** – Exploration and prototyping environments in `notebooks/`

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **OpenAI API key** (set as `OPENAI_API_KEY`)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet

# 2. Configure environment
cp .env.example .env
# Edit .env to add your OPENAI_API_KEY

# 3. Install dependencies
make install

# 4. Launch the fleet (runs frontend + backend)
make dev
# Alternative (backend only): uv run fleet
```

## ✨ Key Features

- **🎯 Magentic-Native Architecture** – Built on Microsoft Agent Framework's `MagenticBuilder` with intelligent planning and progress evaluation
- **🤖 Specialized Agent Fleet** – Pre-configured researcher, coder, and analyst agents with domain-specific tools
- **🌐 Modern Web Frontend** – React-based UI with agent-as-workflow pattern for seamless agent interaction
- **📓 Interactive Notebooks** – Jupyter notebooks for experimentation, prototyping, and learning
- **💾 State Persistence** – Checkpoint system saves 50-80% on retry costs by avoiding redundant LLM calls
- **🛡️ Human-in-the-Loop (HITL)** – Configurable approval gates for code execution, file operations, and sensitive actions
- **📊 Full Observability** – Event-driven callbacks for streaming responses, plan tracking, and tool monitoring
- **🧠 Long-term Memory** – Optional Mem0 integration with Azure AI Search for persistent context
- **🔧 Declarative Configuration** – YAML-based agent configuration for non-engineers to tune prompts and tools
- **🎨 Multiple Interfaces** – CLI, web frontend, and notebooks for different workflows

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **OpenAI API key** (set as `OPENAI_API_KEY`)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Qredence/agentic-fleet.git
cd agentic-fleet

# 2. Configure environment
cp .env.example .env
# Edit .env to add your OPENAI_API_KEY

# 3. Install dependencies
make install

# 4. Launch the fleet (runs frontend + backend)
make dev
# Alternative (backend only): uv run fleet
```

### First Run

**Web Frontend (Default):**
The `make dev` command launches both frontend and backend. Access the web UI at `http://localhost:3000` to interact with agents through a modern React interface using the agent-as-workflow pattern.

**CLI Interface:**
For command-line interaction, run `uv run fleet`:

```text
AgenticFleet v0.5.3
________________________________________________________________________
Task                ➤ Analyze Python code quality in my repository
Plan · Iteration 1  Facts: User needs code analysis | Plan: Use coder agent...
Progress            Status: In progress | Next speaker: coder
Agent · coder       Analyzing repository structure...
Result              Found 12 files, 3 quality issues...
```

**Built-in CLI commands:**

- History navigation: `↑` / `↓` or `Ctrl+R`
- Checkpoints: `checkpoints`, `resume <id>`
- Exit: `quit` or `Ctrl+D`

**Jupyter Notebooks:**
Explore example workflows in `notebooks/` including:

- `magentic.ipynb` – Magentic One pattern examples
- `agent_as_workflow.ipynb` – Agent-as-workflow demonstrations
- `mem0_basic.ipynb` – Memory integration tutorial
- `azure_responses_client.ipynb` – Azure AI responses client usage

---

## 🏗️ Architecture

AgenticFleet implements the **Magentic One** workflow pattern with a manager-executor architecture:

### Workflow Cycle

1. **PLAN** – Manager analyzes task, gathers facts, creates structured action plan
2. **EVALUATE** – Progress ledger checks: request satisfied? in a loop? who acts next?
3. **ACT** – Selected specialist executes with domain-specific tools, returns findings
4. **OBSERVE** – Manager reviews response, updates context, decides next action
5. **REPEAT** – Continues until completion or limits reached (configurable in `workflow.yaml`)

### Agent Specialists

| Agent            | Model Default | Tools                                                 | Purpose                           |
| ---------------- | ------------- | ----------------------------------------------------- | --------------------------------- |
| **Orchestrator** | `gpt-5`       | (none)                                                | Task planning & result synthesis  |
| **Researcher**   | `gpt-5`       | `web_search_tool`                                     | Information gathering & citations |
| **Coder**        | `gpt-5-codex` | `code_interpreter_tool` (Microsoft hosted sandbox)    | Code generation & analysis        |
| **Analyst**      | `gpt-5`       | `data_analysis_tool`, `visualization_suggestion_tool` | Data exploration & insights       |

All agents use **OpenAI Response API** format via `OpenAIResponsesClient` and return structured Pydantic models for reliable downstream parsing.

See **[Architecture Documentation](docs/architecture/magentic-fleet.md)** for detailed design patterns.

---

## ⚙️ Configuration

AgenticFleet uses a **declarative YAML-first** approach:

### Workflow Configuration (`config/workflow.yaml`)

```yaml
fleet:
  manager:
    model: "gpt-5"
    instructions: |
      You coordinate researcher, coder, and analyst agents.
      Delegate based on task requirements...

  orchestrator:
    max_round_count: 30 # Maximum workflow iterations
    max_stall_count: 3 # Triggers replan
    max_reset_count: 2 # Complete restart limit

  callbacks:
    streaming_enabled: true
    log_progress_ledger: true
```

### Per-Agent Configuration (`agents/<role>/config.yaml`)

```yaml
name: researcher
model: gpt-5
temperature: 0.3
max_tokens: 4000

system_prompt: |
  You are a research specialist. Use web_search_tool to find information...

tools:
  - name: web_search_tool
    enabled: true
```

### Environment Variables (`.env`)

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional: Memory (Mem0)
MEM0_HISTORY_DB_PATH=./var/mem0
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Optional: Observability
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4317
```

---

## 🛠️ Development

### Setup Development Environment

```bash
# Install with dev dependencies
make install

# Run configuration validation
make test-config

# Run all quality checks (lint, format, type-check)
make check

# Run test suite
make test
```

### Development Commands

All commands use `uv run` prefix (managed by Makefile):

| Command            | Purpose                                 |
| ------------------ | --------------------------------------- |
| `make dev`         | Launch frontend + backend (full stack)  |
| `make test`        | Run full test suite                     |
| `make test-config` | Validate YAML configs & agent factories |
| `make lint`        | Check code with Ruff                    |
| `make format`      | Auto-format with Black + Ruff           |
| `make type-check`  | Run mypy strict type checking           |
| `make check`       | Chain lint + format + type checks       |

### Testing Patterns

- **Configuration Tests**: `tests/test_config.py` validates env vars, YAML structure, tool imports
- **Fleet Tests**: `tests/test_magentic_fleet.py` covers 14 orchestration scenarios
- **Memory Tests**: `tests/test_mem0_context_provider.py` validates Mem0 integration
- **Mock LLM Calls**: Always patch `OpenAIResponsesClient` to avoid API costs in tests

### Code Quality Standards

- **Python 3.12+** with strict typing (`Type | None` instead of `Optional[Type]`)
- **100-character line limit** (Black formatter)
- **Ruff linting** with `pyupgrade` and `isort` rules
- **MyPy strict checks** (except for test files)
- **Pydantic models** for all tool return types

See **[Contributing Guide](CONTRIBUTING.md)** for detailed conventions.

---

## 📖 Documentation

Comprehensive documentation organized by audience:

### For Users

- **[Getting Started](docs/getting-started/)** – Installation, configuration, first steps
- **[User Guides](docs/guides/)** – Task-oriented tutorials
- **[Agent Catalog](docs/AGENTS.md)** – Detailed agent capabilities & tools
- **[Troubleshooting](docs/troubleshooting/)** – FAQ & common issues

### For Developers

- **[Architecture](docs/architecture/)** – System design & patterns
- **[Features](docs/features/)** – Implementation deep-dives
- **[Contributing](CONTRIBUTING.md)** – Development workflow & standards
- **[API Reference](docs/api/)** – REST API & Python SDK

**[📚 Documentation Index](docs/README.md)** – Complete navigation guide

---

## 🆕 Release Notes

### v0.5.3 (2024-06-15)

- Added analyst agent with data analysis tools
- Improved checkpointing to reduce redundant LLM calls
- Enhanced web frontend with task templates
- Observability improvements: detailed progress ledger logging
- Bug fixes and performance optimizations

---

## 🔧 Adding Custom Agents

Extend the fleet with domain-specific agents:

### 1. Scaffold Agent Structure

```bash
mkdir -p src/agenticfleet/agents/planner/{tools,}
touch src/agenticfleet/agents/planner/{__init__.py,agent.py,config.yaml}
```

### 2. Create Agent Factory

```python
# src/agenticfleet/agents/planner/agent.py
from agenticfleet.config.settings import settings
from agent_framework import ChatAgent
from agent_framework.azure_ai import OpenAIResponsesClient

def create_planner_agent() -> ChatAgent:
    config = settings.load_agent_config("planner")

    return ChatAgent(
        name=config["name"],
        model=config["model"],
        system_prompt=config["system_prompt"],
        client=OpenAIResponsesClient(model_id=config["model"]),
        tools=[],  # Add tools here
    )
```

#

## 🤝 Contributing

We welcome contributions! Please follow these steps:

### Before You Start

1. Read **[Contributing Guidelines](CONTRIBUTING.md)**
2. Review **[Code of Conduct](CODE_OF_CONDUCT.md)**
3. Check existing **[Issues](https://github.com/Qredence/agentic-fleet/issues)**

### Development Process

```bash
# 1. Fork & clone
git clone https://github.com/YOUR_USERNAME/agentic-fleet.git
cd agentic-fleet

# 2. Create feature branch
git checkout -b feat/your-feature

# 3. Make changes
# Edit code, update docs, add tests

# 4. Run quality checks
make check          # Lint, format, type-check
make test-config    # Validate configurations
make test           # Full test suite

# 5. Commit with conventional format
git commit -m "feat(agents): add planner agent with breakdown tool"

# 6. Push & open PR
git push origin feat/your-feature
```

### Pull Request Checklist

- ✅ Tests pass (`make test`)
- ✅ Code formatted (`make check`)
- ✅ Documentation updated
- ✅ YAML configs validated (`make test-config`)
- ✅ Commit messages follow `feat:`, `fix:`, `docs:` convention

---

## 🔐 Security

### Reporting Vulnerabilities

**Do NOT open public issues for security vulnerabilities.**

Please follow the process outlined in **[SECURITY.md](SECURITY.md)**.

### Security Best Practices

- Store API keys in `.env` (never commit)
- Use HITL approval for code execution
- Enable audit logging for sensitive operations
- Review tool permissions in agent configs
- Keep dependencies updated (`uv sync`)

---

## 📄 License

AgenticFleet is released under the **[MIT License](LICENSE)**.

```
Copyright (c) 2025 Qredence

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

See **[LICENSE](LICENSE)** for full terms.

---

## 🙏 Acknowledgments

Built with:

- **[Microsoft Agent Framework](https://github.com/microsoft/agent-framework)** – Core orchestration
- **[Mem0](https://mem0.ai/)** – Long-term memory layer
- **[uv](https://docs.astral.sh/uv/)** – Fast Python package manager
- **[Rich](https://rich.readthedocs.io/)** – Beautiful terminal UI
- **[Pydantic](https://docs.pydantic.dev/)** – Data validation

Special thanks to the Microsoft Agent Framework team for the Magentic One pattern.

---

## 📞 Support & Community

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/Qredence/agentic-fleet/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Qredence/agentic-fleet/discussions)
- **Website**: [qredence.ai](https://qredence.ai)

---

<div align="center">

**[⬆ Back to Top](#agenticfleet)**

Made with ❤️ by [Qredence](https://github.com/Qredence)

</div>
