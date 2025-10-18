#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="$REPO_ROOT/tools/observability/otel-collector-config.yaml"
STATE_DIR="$REPO_ROOT/var/observability"

mkdir -p "$STATE_DIR"

if command -v otelcol >/dev/null 2>&1; then
  echo "[otel-collector] Starting local collector via otelcol binary"
  exec otelcol --config "$CONFIG_FILE"
elif command -v docker >/dev/null 2>&1; then
  echo "[otel-collector] otelcol binary not found; running via docker otel/opentelemetry-collector:latest"
  exec docker run --rm \
    -v "$CONFIG_FILE:/etc/otelcol/config.yaml:ro" \
    -v "$STATE_DIR:/var/lib/otelcol" \
    -p 4317:4317 -p 4318:4318 \
    --name agenticfleet-otel-collector \
    otel/opentelemetry-collector:latest \
    --config /etc/otelcol/config.yaml
else
  echo "[otel-collector] Neither otelcol nor docker is available on PATH." >&2
  echo "Install the OpenTelemetry Collector binary or Docker and retry." >&2
  exit 1
fi
