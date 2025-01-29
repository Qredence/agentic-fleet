# AgenticFleet

A powerful multi-agent system for adaptive AI reasoning and automation. AgenticFleet combines Chainlit's interactive interface with AutoGen's multi-agent capabilities to create a flexible, powerful AI assistant platform.

![Pepy Total Downloads](https://img.shields.io/pepy/dt/agentic-fleet?style=for-the-badge&color=blue)

![GitHub License](https://img.shields.io/github/license/qredence/agenticfleet)
![GitHub forks](https://img.shields.io/github/forks/qredence/agenticfleet)
![GitHub Repo stars](https://img.shields.io/github/stars/qredence/agenticfleet)

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/cf5bcfbdbf50493b9b5de381c24dc147)](https://app.codacy.com/gh/Qredence/AgenticFleet/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

![chainlitlight](https://github.com/user-attachments/assets/0d070c34-e5a8-40be-94f5-5c8307f1f64c)

## Core Components

AgenticFleet operates through a coordinated team of specialized agents:

- **WebSurfer**: Expert web navigation agent
  - Extracts information from web pages
  - Captures and processes screenshots
  - Provides structured summaries of findings

- **FileSurfer**: File system specialist
  - Searches and analyzes workspace files
  - Manages file operations efficiently
  - Extracts relevant information from documents

- **Coder**: Development expert
  - Generates and reviews code
  - Implements solutions
  - Maintains code quality

- **Executor**: Code execution specialist
  - Safely runs code in isolated workspace
  - Monitors execution and handles timeouts
  - Provides detailed execution feedback

## Supported Model Providers

AgenticFleet supports multiple LLM providers through a unified interface:

- **OpenAI**
  - GPT-4 and other OpenAI models
  - Function calling and vision capabilities
  - JSON mode support

- **Azure OpenAI**
  - Azure-hosted OpenAI models
  - Azure AD authentication support
  - Enterprise-grade security

- **Google Gemini**
  - Gemini Pro and Ultra models
  - OpenAI-compatible API
  - Multimodal capabilities

- **DeepSeek**
  - DeepSeek's language models
  - OpenAI-compatible API
  - Specialized model capabilities

- **Ollama**
  - Local model deployment
  - Various open-source models
  - Offline capabilities

- **Azure AI Foundry**
  - Azure-hosted models (e.g., Phi-4)
  - GitHub authentication
  - Enterprise integration

- **CogCache**
  - OpenAI-compatible API with caching
  - Improved response times
  - Cost optimization
  - Automatic retry handling

### Model Provider Installation

Install providers using pip:

```bash
# Install base package
pip install agentic-fleet

# Install all model providers
pip install "agentic-fleet[models]"

# Or install individual providers
pip install "google-cloud-aiplatform>=1.38.0" "google-generativeai>=0.3.0"  # For Gemini
pip install "deepseek>=0.1.0"  # For DeepSeek
pip install "ollama>=0.1.5"  # For Ollama
```

### Model Provider Usage

```python
from agentic_fleet.models import ModelFactory, ModelProvider
from autogen_core.models import UserMessage

# Create Azure OpenAI client
azure_client = ModelFactory.create(
    ModelProvider.AZURE_OPENAI,
    deployment="your-deployment",
    model="gpt-4",
    endpoint="your-endpoint"
)

# Create Gemini client
gemini_client = ModelFactory.create(
    ModelProvider.GEMINI,
    api_key="your-api-key"
)

# Create CogCache client
cogcache_client = ModelFactory.create(
    ModelProvider.COGCACHE,
    api_key="your-cogcache-key",
    model="gpt-4"
)

# Create local Ollama client
ollama_client = ModelFactory.create(
    ModelProvider.OLLAMA,
    model="llama2:latest"
)

# Use any client
async def test_model(client):
    response = await client.create([
        UserMessage(content="What is the capital of France?", source="user")
    ])
    print(response)
```

## Key Features

- **Multi-Agent System**
  - Coordinated team of specialized AI agents
  - Real-time inter-agent communication
  - Task planning and execution tracking
  
- **Interactive Interface**
  - Real-time streaming responses
  - Code syntax highlighting
  - Markdown rendering
  - File upload/download support
  - Progress visualization with task lists

- **Advanced Capabilities**
  - Multiple LLM provider support
  - GitHub OAuth authentication
  - Configurable agent behaviors
  - Comprehensive error handling and recovery
  - Multi-modal content processing (text, images)
  - Execution workspace isolation
  
- **Developer-Friendly**
  - Easy-to-use CLI
  - Extensive documentation
  - Flexible configuration
  - Active community support

## Quick Start

1. Install AgenticFleet using uv (recommended):

```bash
uv pip install agentic-fleet
```

```bash
playwright install --with-deps chromium # Optional: Install Playwright Chromium dependencies
```

2. Copy and configure environment variables:

```bash
# Copy the example environment file
cp .env.example .env

# Open .env and update with your values
# Required: Add your Azure OpenAI credentials
# Optional: Configure OAuth settings
```

3. Start the server:

```bash
agenticfleet start   # Enable GitHub authentication
agenticfleet start --no-oauth # Default local mode
```

The web interface will be available at `http://localhost:8001`.

## System Architecture

```mermaid
graph TD
    User[Chainlit UI] -->|HTTP| App[app.py]
    App --> AgentTeam[MagenticOneGroupChat]
    AgentTeam --> WebSurfer
    AgentTeam --> FileSurfer
    AgentTeam --> Coder
    AgentTeam --> Executor
    WebSurfer -->|Selenium| Web[External Websites]
    FileSurfer -->|OS| FileSystem[Local Files]
    Executor -->|Subprocess| Code[Python/Runtime]
```

## Configuration

The `.env.example` file contains all required and recommended settings:

```env
# Required: Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT=your_deployment
AZURE_OPENAI_MODEL=your_model

# Optional: OAuth Configuration
USE_OAUTH=false # Set to true to enable GitHub OAuth
OAUTH_GITHUB_CLIENT_ID=
OAUTH_GITHUB_CLIENT_SECRET=
OAUTH_REDIRECT_URI=http://localhost:8001/oauth/callback

# Optional: Other Model Provider Configurations
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
GITHUB_TOKEN=your_github_pat  # For Azure AI Foundry
COGCACHE_API_KEY=your_cogcache_key  # For CogCache proxy API
```

## Error Handling

AgenticFleet implements comprehensive error handling:

- Graceful degradation on service failures
- Detailed error logging and reporting
- Automatic cleanup of resources
- Session state recovery
- Execution timeout management

## Development

### Prerequisites

- Python 3.10-3.12 (Python 3.13 is not yet supported)
- uv package manager (recommended)
- Azure OpenAI API access

### Setup

  1. Clone and install:

```bash
git clone https://github.com/qredence/agenticfleet.git
cd agenticfleet
pip install uv
uv pip install -e .
uv pip install -e ".[dev]"
```

2. Run tests:

```bash
pytest tests/
```

## Documentation

- [Installation Guide](docs/installation.md) - Detailed setup instructions
- [Usage Guide](docs/usage-guide.md) - How to use AgenticFleet
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Architecture Overview](docs/agentic-fleet.md) - System architecture and design

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## Security

For security concerns, please review our [Security Policy](SECURITY.md).

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.

## Support

- [Issue Tracker](https://github.com/qredence/agenticfleet/issues)
- [Discussions](https://github.com/qredence/agenticfleet/discussions)
- Email: <contact@qredence.ai>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Qredence/AgenticFleet&type=Date)](https://star-history.com/#Qredence/AgenticFleet&Date)
