# Agentic Fleet
<!-- GitAds-Verify: CUNI4DNKL8JREXW9AFND8MZFG85MZJGT -->

<div align="center">
  
![hero@2x](https://github.com/user-attachments/assets/5c05ab46-cc81-4fe0-9fc4-4ad4e2cb1ad2)

A powerful multi-agent system for adaptive AI reasoning and automation. AgenticFleet combines Chainlit's interactive interface with AutoGen's multi-agent capabilities to create a flexible, powerful AI assistant platform.

[![Weave Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fapp.workweave.ai%2Fapi%2Frepository%2Fbadge%2Forg_X84uIR347D2freSZkxeu4S9S%2F909560351&cacheSeconds=3600)](https://app.workweave.ai/reports/repository/org_X84uIR347D2freSZkxeu4S9S/909560351)
</div>

<div align="center">
  <p>
    <img src="https://img.shields.io/pepy/dt/agentic-fleet?style=for-the-badge&color=blue" alt="Pepy Total Downloads">
    <img src="https://img.shields.io/github/stars/qredence/agenticfleet?style=for-the-badge&color=purple" alt="GitHub Repo stars">
    <img src="https://img.shields.io/github/license/qredence/agenticfleet?style=for-the-badge" alt="GitHub License">
    <img src="https://img.shields.io/github/forks/qredence/agenticfleet?style=for-the-badge" alt="GitHub forks">
    <a href="https://discord.gg/ebgy7gtZHK">
      <img src="https://img.shields.io/discord/ebgy7gtZHK?style=for-the-badge&logo=discord&logoColor=white&label=Discord" alt="Discord">
    </a>
    <a href="https://x.com/agenticfleet">
      <img src="https://img.shields.io/badge/Twitter-Follow-1DA1F2?style=for-the-badge&logo=x&logoColor=white" alt="Twitter Follow">
    </a>
  </p>
</div>

<div align="center">
  <video src="https://github.com/user-attachments/assets/b1ad83ce-b8af-4406-99ed-257a07c0c7cf" autoplay loop muted playsinline width="800">
    <p>Your browser doesn't support HTML5 video. Here is a <a href="assets/b1ad83ce-b8af-4406-99ed-257a07c0c7cf">link to the video</a> instead.</p>
  </video>
</div>

## 🗺️ Short-Term Roadmap

Here's a glimpse into the upcoming features and tasks planned for the near future. This is based on our current open issues:

**🚀 New Features:**

* [#120] NVIDIA Agentiq / NIM / NEMO use
* [#118] OpenAPI documentation
* [#116] Provide a chat history feature
* [#115] LLM model format and handling revamped
* [#114] MCP support
* [#113] Canvas-like interface

**✨ Enhancements & Refinements:**

* [#119] Secure Oauth feature enhancement
* [#117] Simplify entirely the codebase (Review effort: 4)

**🛠️ Tasks & Updates:**

* [#112] Updating Chainlit version dependency

*This roadmap is subject to change based on priorities and development progress. Check the [Issues tab](link-to-your-issues-page) for the most up-to-date status.*


## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Quick Start](#quick-start)
   - [Installation & Environment Setup](#installation--environment-setup)
   - [Running AgenticFleet](#running-agenticfleet)
   - [Using Docker](#using-docker)
4. [Installation Guide](#installation-guide)
   - [Prerequisites](#prerequisites)
   - [Installation Steps](#installation-steps)
   - [Troubleshooting Installation](#troubleshooting-installation)
   - [Optional Feature Sets](#optional-feature-sets)
   - [Warning About Editable Installations](#warning-about-editable-installations)
5. [Model Provider Installation](#model-provider-installation)
6. [Supported Model Providers](#supported-model-providers)
7. [Key Features](#key-features)
8. [Configuration](#configuration)
9. [Error Handling](#error-handling)
10. [Community Contributions](#community-contributions)
11. [Star History](#star-history)
12. [API Overview](#api-overview)
13. [Advanced Configuration](#advanced-configuration)
14. [Supported Features](#supported-features)
15. [Performance Optimization](#performance-optimization)
16. [Contributing](#contributing)
17. [License](#license)

## Introduction

AgenticFleet operates through a coordinated team of specialized agents that work together to provide advanced AI capabilities. This project leverages Chainlit's interactive interface with AutoGen's multi-agent system to deliver robust and adaptive solutions.

A comprehensive platform for deploying, managing, and interacting with AI agents.

## Overview

Agentic Fleet is a sophisticated platform that provides a modular architecture for managing AI agents, tasks, and communication. It supports multiple agent types, task management, and communication channels with a focus on extensibility, allowing for easy integration of new agent types, tools, and interfaces.

## Features

- **Agent Management**: Create, update, and delete AI agents with different capabilities
- **Task Management**: Assign tasks to agents and track their progress
- **Real-time Communication**: Chat interfaces for real-time interaction with agents
- **Multiple Interfaces**: REST API and Chainlit-based UI
- **Tool Integration**: Web search, content generation, and data processing tools
- **Authentication**: API key-based authentication for secure access
- **Logging**: Comprehensive request logging for monitoring and debugging
- **Database Integration**: SQLAlchemy ORM for data persistence

## System Architecture

The Agentic Fleet system is organized into several key components:

### Core Components

1. **API Layer** (`src/agentic_fleet/api/`)
   - FastAPI-based REST API for interacting with the system
   - Endpoints for agent management, task execution, and chat interactions
   - Middleware for authentication, logging, and error handling

2. **Database Layer** (`src/agentic_fleet/database/`)
   - SQLAlchemy ORM models for data persistence
   - Models for agents, messages, and tasks
   - Database session management and connection pooling

3. **Service Layer** (`src/agentic_fleet/services/`)
   - Business logic for agent operations, task management, and chat interactions
   - Client factory for LLM model instantiation and caching
   - Message processing services

4. **Agent System** (`src/agentic_fleet/agents/`)
   - Implementation of agent types (e.g., MagenticOne)
   - Agent registration and discovery
   - Agent execution and lifecycle management

5. **Tools** (`src/agentic_fleet/tools/`)
   - Utility tools available to agents
   - Web search capabilities (Google, Bing)
   - Content generation (images, PDFs)
   - Web page fetching and data extraction

6. **UI Layer** (`src/agentic_fleet/ui/`)
   - Chainlit-based chat interface
   - Settings management
   - Task visualization and management
   - Message handling and formatting

7. **Configuration System** (`src/agentic_fleet/config/`)
   - YAML-based configuration for agents, models, and system settings
   - Environment variable integration
   - Configuration validation and loading

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL (optional, for production)
- API keys for external services (OpenAI, Google, Bing, etc.)
- Node.js (for UI development)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/agentic-fleet.git
   cd agentic-fleet
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   # Using the provided script
   ./install_deps.sh
   
   # Or using make
   make install
   
   # Or manually with pip
   pip install -r requirements.txt
   
   # Or install directly from source with development dependencies
   pip install -e ".[dev]"
   ```

4. Create a `.env` file:
   ```
   HOST=0.0.0.0
   PORT=8000
   CHAINLIT_PORT=8001
   RELOAD=True
   API_KEY=your_secret_api_key  # Optional, for authentication
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/agentic_fleet  # Optional, for production
   OPENAI_API_KEY=your_openai_api_key  # Required for LLM functionality
   GOOGLE_API_KEY=your_google_api_key  # Optional, for Google Search tool
   BING_API_KEY=your_bing_api_key  # Optional, for Bing Search tool
   ```

### Running the Application

#### API Server

```bash
# Using make
make run

# Or directly with Python
python -m agentic_fleet.main

# Or using the installed entry point
agentic-fleet
```

The API will be available at `http://localhost:8000`.

- API Documentation: `http://localhost:8000/docs`
- Alternative Documentation: `http://localhost:8000/redoc`

#### Chainlit UI

```bash
# Run the Chainlit UI
python -m agentic_fleet.app
```

The Chainlit UI will be available at `http://localhost:8001`.

## API Endpoints

### Agents

- `GET /agents`: List all agents
- `POST /agents`: Create a new agent
- `GET /agents/{agent_id}`: Get agent details
- `PUT /agents/{agent_id}`: Update an agent
- `DELETE /agents/{agent_id}`: Delete an agent

### Tasks

- `GET /tasks`: List all tasks
- `POST /tasks`: Create a new task
- `GET /tasks/{task_id}`: Get task details
- `PUT /tasks/{task_id}`: Update a task
- `DELETE /tasks/{task_id}`: Delete a task
- `POST /tasks/{task_id}/assign/{agent_id}`: Assign a task to an agent

### Chat

- `GET /chat/messages`: List all chat messages
- `POST /chat/messages`: Create a new chat message
- `GET /chat/messages/{message_id}`: Get message details
- `PUT /chat/messages/{message_id}`: Update a message
- `DELETE /chat/messages/{message_id}`: Delete a message
- `WebSocket /chat/ws`: Real-time chat endpoint

## User Interfaces

### Chainlit UI

The system provides a web-based chat interface using Chainlit:

1. **Chat Interface**
   - Real-time messaging with agents
   - File upload and sharing
   - Message history and threading

2. **Settings Management**
   - Model selection and configuration
   - Temperature and other generation parameters
   - Agent selection and customization

3. **Task Management**
   - Task creation and assignment
   - Task status tracking
   - Task prioritization

## Agent System

### Agent Types

1. **MagenticOne**
   - Based on the AutoGen framework
   - Supports code execution and reasoning
   - Human-in-the-loop capabilities
   - Uses a team of specialized agents including:
     - Orchestrator: Manages the conversation flow
     - Coder: Writes and executes code
     - WebSurfer: Browses and retrieves web content
     - FileSurfer: Searches and manipulates files
     - ComputerTerminal: Executes terminal commands

### Agent Capabilities

- Natural language understanding and generation
- Tool usage (web search, content generation, etc.)
- Task planning and execution
- Memory and context management
- Code execution in a sandboxed environment
- Web browsing and information retrieval
- File operations and document processing

## Tools and Utilities

The system provides several tools that agents can use:

1. **Search Tools**
   - Google Search
   - Bing Search

2. **Content Generation**
   - Image generation
   - PDF generation

3. **Web Interaction**
   - Webpage fetching and parsing
   - Browser automation

4. **Utility Tools**
   - Calculator
   - Data processing
   - File operations

## Development

### Project Structure

```
agentic_fleet/
├── src/
│   └── agentic_fleet/
│       ├── agents/              # Agent implementations
│       ├── api/                 # API endpoints and middleware
│       │   ├── dependencies/
│       │   ├── middleware/
│       │   ├── routes/
│       │   └── app.py
│       ├── apps/                # Application modules
│       ├── config/              # Configuration system
│       ├── core/                # Core functionality
│       │   ├── application/
│       │   ├── llm/
│       │   └── workflows/
│       ├── database/            # Database models and session
│       │   ├── models/
│       │   └── session.py
│       ├── exceptions/          # Custom exceptions
│       ├── message_processing/  # Message handling
│       ├── models/              # Data models
│       ├── schemas/             # Pydantic schemas
│       ├── services/            # Business logic
│       ├── shared/              # Shared utilities
│       ├── tools/               # Agent tools
│       ├── ui/                  # User interface
│       │   ├── chainlit/
│       │   └── message_handler.py
│       ├── utils/               # Utility functions
│       ├── app.py               # Chainlit application
│       └── main.py              # FastAPI application
├── tests/
├── .env
├── pyproject.toml
├── requirements.txt
├── Makefile
└── README.md
```

### Development Commands

The project includes a Makefile with common development commands:

```bash
# Install dependencies
make install

# Run tests
make test

# Run linting
make lint

# Format code
make format

# Clean build artifacts
make clean

# Run the application
make run

# Show help
make help
```

### Running Tests

```bash
# Using make
make test

# Or directly with pytest
pytest
```

### Adding New Components

1. **New Agent Types**
   - Create a new file in `agents/`
   - Implement the agent interface
   - Register the agent in `agents/__init__.py`

2. **New Tools**
   - Create a new file in `tools/`
   - Implement the tool interface
   - Register the tool in `tools/__init__.py`

3. **New API Endpoints**
   - Create a new file in `api/routes/`
   - Implement the endpoint handlers
   - Register the routes in `api/routes/__init__.py`

## Configuration

The system uses a hierarchical configuration system:

1. **Environment Variables**
   - Runtime configuration
   - Sensitive information (API keys, credentials)

2. **YAML Configuration Files**
   - Agent definitions
   - Model configurations
   - Memory settings

3. **Dynamic Configuration**
   - User preferences
   - Session settings

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=qredence/agenticfleet&type=Date)](https://www.star-history.com/#qredence/agenticfleet&Date)
