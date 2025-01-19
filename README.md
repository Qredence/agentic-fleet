# AgenticFleet

A powerful multi-agent system for adaptive AI reasoning and automation. AgenticFleet combines Chainlit's interactive interface with AutoGen's multi-agent capabilities to create a flexible, powerful AI assistant platform.

<div align="left">
<a href="https://pypi.org/project/agentic-fleet/">
   <img alt="Pepy Total Downlods" src="https://img.shields.io/pepy/dt/agentic-fleet">
</a>
<img alt="GitHub License" src="https://img.shields.io/github/license/qredence/agenticfleet">
<img alt="GitHub forks" src="https://img.shields.io/github/forks/qredence/agenticfleet">
<img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/qredence/agenticfleet">
</div>

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/cf5bcfbdbf50493b9b5de381c24dc147)](https://app.codacy.com/gh/Qredence/AgenticFleet/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

![chainlitlight](https://github.com/user-attachments/assets/0d070c34-e5a8-40be-94f5-5c8307f1f64c)

## Key Features

- **Multi-Agent System**: Coordinated team of specialized AI agents
  - Code generation and analysis
  - Web content processing
  - File system operations
  
- **Interactive Interface**
  - Real-time communication via Chainlit
  - Code syntax highlighting
  - Markdown rendering
  - File upload/download support

- **Advanced Capabilities**
  - OAuth authentication integration
  - Configurable agent behaviors
  - Comprehensive error handling
  - Progress tracking
  
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
playwright install --with-deps chromium
```


2. Copy and configure environment variables:

```bash
# Copy the example environment file
cp .env.example .env

# Open .env and update with your values
# Required: Add your Azure OpenAI credentials
# Recommended: Configure OAuth settings
```

3. Start the server:

```bash
agenticfleet start
```

The web interface will be available at `http://localhost:8001`.

## Documentation

- [Installation Guide](docs/installation.md) - Detailed setup instructions
- [Usage Guide](docs/usage-guide.md) - How to use AgenticFleet
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Architecture Overview](docs/agentic-fleet.md) - System architecture and design

## Configuration

The `.env.example` file contains all required and recommended settings. Copy it to `.env` and update with your values:

```env
# Required: Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT=your_deployment
AZURE_OPENAI_MODEL=your_model

## Recommended: OAuth Configuration
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
OAUTH_REDIRECT_URI=http://localhost:8001/oauth/callback
```

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
uv pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest tests/
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## Security

For security concerns, please review our [Security Policy](SECURITY.md).

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.

## Support

- [Issue Tracker](https://github.com/qredence/agenticfleet/issues)
- [Discussions](https://github.com/qredence/agenticfleet/discussions)
- Email: contact@qredence.ai
