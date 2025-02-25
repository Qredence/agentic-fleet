#!/bin/bash
set -e

# Print environment information
echo "🚀 Starting AgenticFleet Docker container"
echo "📂 Current directory: $(pwd)"
echo "🐍 Python version: $(python --version)"
echo "📦 Pip version: $(pip --version)"

# Check if we're in development mode
if [ "$DEBUG" = "true" ]; then
    echo "🔧 Running in DEVELOPMENT mode"
    
    # Install package in development mode if not already installed
    if ! pip show agentic-fleet &>/dev/null; then
        echo "📥 Installing package in development mode..."
        pip install -e .
    else
        echo "✅ Package already installed in development mode"
    fi
    
    # Install development dependencies if needed
    if [ "$INSTALL_DEV_DEPS" = "true" ]; then
        echo "📥 Installing development dependencies..."
        pip install ".[dev,test]"
    fi
else
    echo "🚀 Running in PRODUCTION mode"
fi

# Check for required environment variables
required_vars=("AZURE_OPENAI_ENDPOINT" "AZURE_OPENAI_API_KEY" "AZURE_OPENAI_API_VERSION")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Error: Missing required environment variables: ${missing_vars[*]}"
    echo "Please set these variables in your .env file or pass them to docker-compose"
    exit 1
fi

echo "🔄 Command to execute: $@"
# Run the command
exec "$@"
