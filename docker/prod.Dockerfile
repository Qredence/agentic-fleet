# Production Dockerfile for AgenticFleet
# This file is symlinked from the root directory as /workspace/Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright dependencies
RUN pip install playwright && python -m playwright install-deps

# Copy the project files
COPY . .

# Install the package
RUN pip install .

# Expose the port Chainlit runs on
EXPOSE 8000

# Set the default command to run the Chainlit application
CMD ["chainlit", "run", "src/agentic_fleet/app.py", "--host", "0.0.0.0", "--port", "8000"]
