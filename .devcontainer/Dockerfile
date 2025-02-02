FROM python:3.12-slim

# Build arguments for all configurable values
ARG VERSION=0.4.71
# Azure OpenAI
ARG AZURE_OPENAI_API_KEY
ARG AZURE_OPENAI_ENDPOINT
ARG AZURE_OPENAI_DEPLOYMENT
ARG AZURE_OPENAI_MODEL
# OAuth
ARG USE_OAUTH=true
ARG OAUTH_GITHUB_CLIENT_ID
ARG OAUTH_GITHUB_CLIENT_SECRET
# Other APIs
ARG OPENAI_API_KEY
ARG GEMINI_API_KEY
ARG DEEPSEEK_API_KEY
ARG COGCACHE_API_KEY
ARG RUN_MODE=default

# Set build arguments as environment variables
ENV VERSION=${VERSION}
ENV AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
ENV AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
ENV AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT}
ENV AZURE_OPENAI_MODEL=${AZURE_OPENAI_MODEL}
ENV USE_OAUTH=${USE_OAUTH}
ENV OAUTH_GITHUB_CLIENT_ID=${OAUTH_GITHUB_CLIENT_ID}
ENV OAUTH_GITHUB_CLIENT_SECRET=${OAUTH_GITHUB_CLIENT_SECRET}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV GEMINI_API_KEY=${GEMINI_API_KEY}
ENV DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
ENV COGCACHE_API_KEY=${COGCACHE_API_KEY}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy requirements first to leverage Docker cache
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install hatch && \
    pip install -e ".[dev,test]"

# Install Playwright dependencies
RUN npx playwright install-deps && \
    playwright install chromium

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace
ENV PORT=8001

# Expose port
EXPOSE 8001

# Set entrypoint script
COPY scripts/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["sh", "-c", "agenticfleet start ${RUN_MODE:+no-oauth}"]