# Agentic Fleet v2.0

Agentic Fleet is a modular orchestration framework for multi-agent systems, leveraging the **Microsoft Agent Framework** for orchestration and **DSPy** for type-safe cognitive reasoning. It implements a self-improving (GEPA) architecture with hierarchical skill management and dynamic routing.

## 🚀 Overview

- **Modular Architecture**: Holistic separation of concerns between agents, cognitive modules, and workflows.
- **Type-Safe Cognition**: Uses DSPy and Pydantic for robust, validated LLM outputs.
- **Self-Improvement (GEPA)**: Goal-Oriented Evolutionary Prompt Architecture for automatic optimization of planner strategies.
- **Hierarchical Skills**: A structured taxonomy for agent capabilities with HitL (Human-in-the-Loop) approval workflows.
- **Dynamic Routing**: Intelligent task distribution via a router agent and conditional workflow graphs.
- **Multi-Provider Support**: Direct integration with DeepInfra, Gemini, and GLM (via Anthropic SDK).

## 🛠 Tech Stack

- **Language**: Python 3.13+
- **Orchestration**: Microsoft Agent Framework
- **Reasoning**: DSPy (v3.0+)
- **API Framework**: FastAPI & WebSockets
- **Database**: SQLModel (SQLAlchemy + Pydantic) with SQLite (default)
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **LLM SDKs**: `openai`, `google-genai`, `anthropic`

## 📋 Requirements

- Python 3.13.9 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- LLM API Keys (DeepInfra, Google, or ZAI)

## ⚙️ Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd agentic-fleet
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the root directory (see [Environment Variables](#-environment-variables) for details).

## 🏃 Running the Application

### Development Server
Start the FastAPI server with auto-reload:
```bash
uv run uvicorn --app-dir src agentic_fleet.main:app --reload
```

### Endpoints
- **HTTP**: `POST /run` - Execute a workflow message.
- **Websocket**: `WS /ws` - Real-time interaction.
- **Training**: `POST /train` - Compile DSPy modules using collected traces.
- **Skill Management**: `GET/POST/PUT/DELETE /skills` - Manage the skill repository.

## 🧪 Testing

### Run All Tests
```bash
uv run pytest
```

### Phase Verification Scripts
Specific smoke tests for architectural phases:
```bash
uv run python tests/verify_phase_2.py
uv run python tests/verify_phase_3.py
uv run python tests/verify_phase_5.py
```

## 📂 Project Structure

```text
.
├── src/agentic_fleet/
│   ├── agents/          # Agent Framework implementations (Router, BaseAgent)
│   ├── dspy_modules/    # DSPy signatures, modules, and validators
│   ├── gepa/            # Optimization & Trace collection (Self-improvement)
│   ├── middleware/      # Context management & Modulators
│   ├── skills/          # Hierarchical skill management & HitL approval
│   ├── workflows/       # Workflow graph definitions
│   ├── config.py        # Team registry and global settings
│   ├── db.py            # SQLModel schema and database engine
│   ├── llm.py           # Provider SDK routing and LM configuration
│   └── main.py          # FastAPI entry point
├── tests/               # Unit and integration tests
├── docs/                # Project documentation
├── pyproject.toml       # Dependencies and build config
└── AGENTS.md            # Agent-specific documentation & conventions
```

## 🔑 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./fleet.db` |
| `FLEET_STATE_DIR` | Directory for optimized DSPy state | `.context/state` |
| `DSPY_MODEL` | Default DSPy model alias | `deepseek-v3.2` |
| `FLEET_MODEL_ROUTING` | Enable/Disable per-role routing (0 to disable) | `1` |
| `DEEPINFRA_API_KEY` | API Key for DeepInfra (OpenAI SDK) | - |
| `GOOGLE_API_KEY` | API Key for Gemini (Google SDK) | - |
| `ZAI_API_KEY` | API Key for GLM (Anthropic SDK) | - |
| `ZAI_ANTHROPIC_BASE_URL` | Base URL for ZAI Anthropic-compatible API | - |

See [MODEL_MAP.md](MODEL_MAP.md) for detailed LLM routing configuration.

## 📜 License

TODO: Add license information.

---
*For internal developer conventions and detailed command lists, see [AGENTS.md](AGENTS.md).*
