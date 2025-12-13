#!/bin/bash
# Quick start script for tracing visualization with AgenticFleet

set -e

echo "🚀 AgenticFleet Tracing Visualization Setup"
echo "==========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "ℹ️  docker-compose not found, trying 'docker compose'..."
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "✅ Docker found: $(docker --version)"
echo ""

# Start the tracing collector
echo "🔧 Starting OpenTelemetry Collector with Jaeger..."
${DOCKER_COMPOSE} -f docker/docker-compose.tracing.yml up -d

echo "✅ Collector started!"
echo ""

# Wait for collector to be ready
echo "⏳ Waiting for collector to be ready..."
# Wait for collector to be ready
echo "⏳ Waiting for collector to be ready..."
if ! command -v curl &> /dev/null; then
    echo "⚠️  curl not found, skipping readiness check (verify manually at http://localhost:16686)"
else
    for i in {1..30}; do
        if curl -s http://localhost:16686/api/services > /dev/null 2>&1; then
            echo "✅ Collector is ready!"
            break
        fi
        echo -n "."
        sleep 1
    done
fi

echo ""
echo "==========================================="
echo "✨ Tracing is now active!"
echo ""
echo "📊 View traces at: http://localhost:16686"
echo ""
echo "🚀 Next steps:"
echo "   1. Start the backend: make backend"
echo "   2. Run a workflow: agentic-fleet run -m 'Your task here'"
echo "   3. Open http://localhost:16686 and select 'agentic-fleet' service"
echo ""
echo "🛑 To stop the collector later, run:"
echo "   ${DOCKER_COMPOSE} -f docker/docker-compose.tracing.yml down"
echo ""
