# Docker Setup for AgenticFleet

This directory contains the Docker configuration for AgenticFleet, providing a modular and flexible approach to containerization.

## Docker Files Structure

- `base.Dockerfile`: Base image with core dependencies
- `dev.Dockerfile`: Development environment with additional tools and live-reload
- `prod.Dockerfile`: Production-optimized image
- `docker-compose.yml`: Docker Compose configuration for all environments
- `.dockerignore`: Files to exclude from Docker builds

## Quick Start

### Development Environment

```bash
# Build and start the development environment
docker-compose up -d dev

# View logs
docker-compose logs -f dev
```

### Production Environment

```bash
# Build and start the production environment
docker-compose up -d prod

# View logs
docker-compose logs -f prod
```

## Manual Building

You can also build the Docker images manually using the provided script:

```bash
# Build the base image
./scripts/docker-build.sh base

# Build the development image
./scripts/docker-build.sh dev

# Build the production image
./scripts/docker-build.sh prod

# Build and push the production image to Docker Hub
./scripts/docker-build.sh prod --push
```

## Symlinks in Root Directory

For convenience, the following symlinks are available in the project root:

- `Dockerfile` → `docker/prod.Dockerfile`
- `docker-compose.yml` → `docker/docker-compose.yml`
- `.dockerignore` → `docker/.dockerignore`

These symlinks allow you to run Docker commands directly from the root directory.

## Environment Variables

The Docker containers require certain environment variables to function properly. You can provide these variables in a `.env` file in the project root or pass them directly to the container.

Required environment variables:

- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI API endpoint
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_API_VERSION`: Azure OpenAI API version

See `.env.example` for a complete list of supported environment variables.

## Volumes

The development environment mounts the following volumes:

- `.:/app`: The project root directory for live code changes
- `./logs:/app/logs`: Logs directory for persistent logs

## Ports

Both development and production environments expose port 8000, which can be accessed at `http://localhost:8000`.

## Customization

You can customize the Docker setup by modifying the `docker-compose.yml` file or the individual Dockerfiles in this directory.
