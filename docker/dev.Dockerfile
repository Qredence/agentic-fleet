# Development Dockerfile for AgenticFleet
FROM qredenceai/agenticfleet-base:latest

# Install development dependencies
RUN pip install --no-cache-dir ".[dev,test]"

# Set environment variables for development
ENV DEBUG=true \
    LOG_LEVEL=DEBUG

# Expose the port Chainlit runs on
EXPOSE 8000

# Set the default command to run the Chainlit application in development mode
CMD ["chainlit", "run", "src/agentic_fleet/app.py", "--host", "0.0.0.0", "--port", "8000"]
