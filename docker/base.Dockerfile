# Base Dockerfile for AgenticFleet
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Set the working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright dependencies
RUN python -m playwright install-deps

# Copy the project files
COPY . .

# Install the package in development mode
RUN pip install -e .
