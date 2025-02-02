FROM python:3.12-slim

# Build argument for version only
ARG VERSION=0.4.71

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
ENV VERSION=${VERSION}

# Default values for optional settings
ENV USE_OAUTH=false
ENV CHAINLIT_HOST=localhost
ENV CHAINLIT_PORT=8001

# Expose port
EXPOSE 8001

# Copy entrypoint script
COPY scripts/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command
CMD ["agenticfleet", "start"]