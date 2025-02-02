# Use Debian-based Python image
FROM python:3.12-slim-bullseye

# Build argument for version only
ARG VERSION=0.4.71

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    nodejs \
    npm \
    chromium \
    libnss3 \
    libfreetype6 \
    libharfbuzz0b \
    ca-certificates \
    fonts-freefont-ttf \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory to where app.py and cli.py are located
WORKDIR /src/agentic_fleet

# Copy the entire application code into the working directory
COPY . .

# Install Python dependencies (excluding dev and test)
RUN pip install --upgrade pip && \
    pip install hatch && \
    pip install playwright chainlit && \
    playwright install chromium && \
    pip install -e .

# Set environment variables for Playwright and Chainlit
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/bin/chromium \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    CHAINLIT_HOST=0.0.0.0 \
    CHAINLIT_PORT=8001

# Default environment variables for Azure OpenAI (can be overridden at runtime)
ENV AZURE_OPENAI_API_KEY="" \
    AZURE_OPENAI_ENDPOINT="" \
    AZURE_OPENAI_DEPLOYMENT="" \
    AZURE_OPENAI_MODEL="" \
    USE_OAUTH="false"

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

# Copy entrypoint script from the correct path
COPY scripts/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command
CMD ["chainlit", "run", "/src/agentic_fleet/src/agentic_fleet/app.py", "--host", "0.0.0.0", "--port", "8001"]