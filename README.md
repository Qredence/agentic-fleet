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

### 4. Run the Application

```bash
python main.py
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