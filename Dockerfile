# syntax=docker/dockerfile:1
# ============================================================================
# AgenticFleet Backend Dockerfile
# Optimized multi-stage build for production
# ============================================================================

FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only dependency files first (better caching)
COPY pyproject.toml uv.lock ./

# Sync dependencies WITHOUT installing the project itself
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and install project
COPY src/agentic_fleet ./src/agentic_fleet
COPY README.md LICENSE ./
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Runtime stage - minimal image
# -----------------------------------------------------------------------------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash app

WORKDIR /app

# Copy only the virtual environment and source
COPY --from=builder --chown=app:app /app/.venv ./.venv
COPY --from=builder --chown=app:app /app/src ./src

# Create data directories with correct permissions
RUN mkdir -p .var/logs .var/cache .var/data && chown -R app:app .var

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "agentic_fleet.main:app", "--host", "0.0.0.0", "--port", "8000"]
