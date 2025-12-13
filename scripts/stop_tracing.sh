#!/bin/bash
# Stop tracing visualization

set -e

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "🛑 Stopping OpenTelemetry Collector and Jaeger..."
${DOCKER_COMPOSE} -f docker/docker-compose.tracing.yml down

echo "✅ Tracing stopped."
echo ""
echo "📊 Traces are preserved in Docker. To view them again, run:"
echo "   ./scripts/start_tracing.sh"
echo ""
