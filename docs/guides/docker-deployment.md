# Docker Deployment

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# 2. Start services
docker compose up -d

# 3. Access
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

## Commands

```bash
docker compose up -d                    # Start all
docker compose up -d backend            # Backend only
docker compose --profile tracing up -d  # With Jaeger tracing
docker compose logs -f                  # View logs
docker compose down                     # Stop
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `TAVILY_API_KEY` | No | Web search |
| `AZURE_OPENAI_*` | No | Azure OpenAI config |
| `ENABLE_OTEL` | No | Enable tracing |

## Production

For production, use pre-built images:

```bash
docker pull ghcr.io/qredence/agentic-fleet:latest
docker pull ghcr.io/qredence/agentic-fleet-ui:latest
```

Or build locally:
```bash
docker compose build
```
