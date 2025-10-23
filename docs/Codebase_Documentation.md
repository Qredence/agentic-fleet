# AgenticFleet Codebase Documentation

## 1. Introduction

AgenticFleet is a comprehensive framework for building and managing multi-agent systems. It provides a flexible and extensible architecture for creating sophisticated agent-based workflows. The framework is designed to be highly configurable and observable, with a focus on developer experience and ease of use.

### Key Features

* **Magentic-Native Architecture:** Built on the Microsoft Agent Framework's `MagenticBuilder`, AgenticFleet provides intelligent planning and progress evaluation.
* **Specialized Agent Fleet:** The framework includes a pre-configured fleet of specialized agents, including a researcher, a coder, and an analyst, each with its own set of domain-specific tools.
* **Modern Web Frontend:** A React-based web frontend provides a user-friendly interface for interacting with the agent fleet.
* **Interactive Notebooks:** Jupyter notebooks are provided for experimentation, prototyping, and learning.
* **State Persistence:** A checkpoint system saves the state of the workflow, allowing for cost savings on retries.
* **Human-in-the-Loop (HITL):** The framework includes a configurable approval system for sensitive operations, such as code execution and file operations.
* **Full Observability:** The framework is fully observable, with an event-driven callback system for streaming responses, plan tracking, and tool monitoring.
* **Long-term Memory:** Optional integration with Mem0 provides long-term memory for the agent fleet.
* **Declarative Configuration:** The framework uses a declarative YAML-based configuration system, allowing for easy customization of agent prompts and tools.
* **Multiple Interfaces:** The framework provides multiple interfaces for interacting with the agent fleet, including a CLI, a web frontend, and Jupyter notebooks.

## 2. Architecture

AgenticFleet follows a hybrid modular monolith architecture with event-driven orchestration and plugin-based agent factories.

* **Backend:** The backend is built with Python 3.12+, using the Microsoft Agent Framework (Magentic pattern), FastAPI, Pydantic, and an OpenAI Responses API client. It uses Redis for optional caching and SQLite for conversation storage.
* **Frontend:** The frontend is a modern React 18 application built with Vite, TypeScript, Tailwind CSS, and shadcn/ui. It uses Server-Sent Events (SSE) for real-time streaming of agent responses.
* **Tooling:** The project uses `uv` for Python dependency management, `make` for task automation, and a suite of tools for code quality, including Ruff, Black, and mypy.

## 3. Backend

The backend is organized into several Python packages, each with a specific responsibility.

### `agenticfleet`

This is the main Python package for the AgenticFleet framework.

#### `agents`

This package contains the different types of agents in the fleet. Each agent is a specialized `ChatAgent` with its own set of instructions and tools.

* **`analyst`:** An agent for data analysis and visualization.
* **`coder`:** An agent for code generation and analysis.
* **`orchestrator`:** The main agent responsible for planning and coordinating the other agents.
* **`researcher`:** An agent for gathering information from the web.

#### `cli`

This package contains the command-line interface for interacting with the AgenticFleet framework.

* **`af.py`:** The main entry point for the CLI.
* **`repl.py`:** The Read-Eval-Print Loop (REPL) for the CLI.
* **`ui.py`:** The user interface for the CLI.

#### `config`

This package is responsible for managing the configuration of the AgenticFleet framework.

* **`settings.py`:** Defines the Pydantic models for the configuration settings.
* **`workflow.yaml`:** The main configuration file for the workflow, defining the agents, their prompts, and their tools.

#### `context`

This package is responsible for managing the context of the conversation, including the long-term memory.

* **`mem0_provider.py`:** A context provider that uses Mem0 for long-term memory.

#### `core`

This package contains the core components of the AgenticFleet framework.

* **`approval.py`:** The approval mechanism for sensitive operations.
* **`checkpoints.py`:** The checkpoint system for saving the state of the workflow.
* **`exceptions.py`:** The custom exception hierarchy for the framework.
* **`logging.py`:** The logging configuration for the framework.

#### `fleet`

This package contains the orchestration layer for the AgenticFleet framework.

* **`magentic_fleet.py`:** The main orchestrator for the agent fleet.
* **`fleet_builder.py`:** A builder for constructing the agent fleet.
* **`callbacks.py`:** The event-driven callback system for streaming responses.

#### `haxui`

This package contains the FastAPI backend for the web UI.

* **`api.py`:** The main API for the web UI.
* **`sse_events.py`:** The Server-Sent Events (SSE) for real-time streaming of agent responses.

#### `workflows`

This package contains the workflow definitions for the AgenticFleet framework.

* **`workflow_as_agent.py`:** A workflow that is executed as an agent.

## 4. Frontend

The frontend is a modern React application that provides a user-friendly interface for interacting with the agent fleet.

### `src`

This is the main source directory for the frontend application.

#### `components`

This directory contains reusable React components.

#### `hooks`

This directory contains custom React hooks.

#### `pages`

This directory contains the main pages of the web application.

#### `lib`

This directory contains utility functions for the frontend application.

## 5. Getting Started

### Prerequisites

* Python 3.12+
* `uv` package manager
* OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Qredence/agentic-fleet.git
   cd agentic-fleet
   ```
2. Configure the environment:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file to add your OpenAI API key.
3. Install the dependencies:
   ```bash
   make install
   ```
4. Launch the fleet:
   ```bash
   make dev
   ```
   This will start both the frontend and the backend. The frontend will be available at `http://localhost:5173`, and the backend will be available at `http://localhost:8000`.

### Running Tests

To run the test suite, use the following command:

```bash
make test
```

## 6. Contributing

Contributions are welcome! Please refer to the [Contributing Guidelines](CONTRIBUTING.md) for more information.
