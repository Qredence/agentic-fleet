# Use Alpine as the base image
FROM python:3.12-alpine

# Build argument for version only
ARG VERSION=0.4.71

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    git \
    curl \
    nodejs \
    npm

# Set the working directory to where app.py and cli.py are located
WORKDIR /src/agentic_fleet

# Copy the entire application code into the working directory
COPY . .

# Install Python dependencies (excluding dev and test)
RUN pip install --upgrade pip && \
    pip install hatch && \
    pip install .

# Install Playwright dependencies and Chromium
RUN npx playwright install-deps && \
    npx playwright install chromium

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
CMD ["agenticfleet", "start"]