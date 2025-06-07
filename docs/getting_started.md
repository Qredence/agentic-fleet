# Getting Started with AgenticFleet

This guide will help you get up and running with AgenticFleet quickly.

## Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended) or `pip`
- A supported model provider (Azure OpenAI, OpenAI, or others)

## Installation

1. **Install AgenticFleet:**
   ```bash
   uv pip install agentic-fleet
   ```

2. **Install Browser Dependencies:**
   ```bash
   uv pip install playwright
   playwright install --with-deps chromium
   ```

## Environment Setup

1. **Create Environment File:**
   ```bash
   cp .env.example .env
   ```

2. **Configure Environment Variables:**
   Open `.env` and set these required variables:
   ```env
   # Required: Azure OpenAI Configuration
   AZURE_OPENAI_API_KEY=your_api_key
   AZURE_OPENAI_ENDPOINT=your_endpoint
   AZURE_OPENAI_DEPLOYMENT=your_deployment
   AZURE_OPENAI_MODEL=your_model

   # Optional: OAuth Configuration (if using authentication)
   USE_OAUTH=true
   OAUTH_GITHUB_CLIENT_ID=your_client_id
   OAUTH_GITHUB_CLIENT_SECRET=your_client_secret
   ```

## Running AgenticFleet

The primary way to run AgenticFleet is by executing its main module:

```bash
python -m agentic_fleet.main
```

This command starts the FastAPI server. By default:
- The API will be available at `http://localhost:8000`.
- The interactive Chainlit UI will be available at `http://localhost:8000/ui`.
- The OpenAPI documentation can be accessed at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc).

You can configure the `HOST` and `PORT` via environment variables (see `.env` file).

### Using Docker

1.  **Pull the Image:**
    ```bash
    docker pull qredence/agenticfleet:latest
    ```

2.  **Run the Container:**
    Ensure you pass the necessary environment variables for your chosen model provider (e.g., Azure OpenAI). The application inside the container listens on port 8000 by default.
    ```bash
    docker run -d -p 8001:8000 \
      -e AZURE_OPENAI_API_KEY=your_key \
      -e AZURE_OPENAI_ENDPOINT=your_endpoint \
      -e AZURE_OPENAI_DEPLOYMENT=your_deployment \
      -e AZURE_OPENAI_MODEL=your_model \
      qredence/agenticfleet:latest
    ```
    You can then access the UI at `http://localhost:8001/ui`.

## Verifying Installation

1. Start AgenticFleet using the method above.
2. Open your browser to `http://localhost:8000/ui` (or `your_host:your_port/ui` if you configured custom host/port).
3. You should see the AgenticFleet Chainlit interface. The API documentation is available at `http://localhost:8000/docs`.

## Next Steps

- Read the [Configuration Guide](configuration.md) for detailed settings
- Check out the [CLI Commands Reference](cli_commands.md) for available commands
- See the [API Reference](api_reference.md) for programmatic usage
- Visit the [Troubleshooting Guide](troubleshooting.md) if you encounter issues
