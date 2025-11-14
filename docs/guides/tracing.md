# Tracing & Observability Guide

This guide explains how to enable, configure, and use tracing for the DSPy-Enhanced Agent Framework.

## Overview

Tracing provides deep visibility into multi-agent workflow execution. Using the **agent-framework**'s built-in OpenTelemetry instrumentation you automatically get spans for:

- Agent creation & lifecycle
- Chat client requests (prompt + completion latency)
- DSPy compilation (BootstrapFewShot / GEPA) when enabled
- Workflow phases (routing, execution, refinement)
- Tool invocations (when instrumented by underlying SDK)

If the agent-framework observability helper is unavailable the framework falls back to manual OpenTelemetry setup.

## Configuration Methods

### YAML (Preferred)

Add a `tracing` section to `config/workflow_config.yaml`:

```yaml
tracing:
  enabled: true
  otlp_endpoint: http://localhost:4317 # OTLP gRPC port (NOT 16686 which is Jaeger UI)
  capture_sensitive: true # Export prompts & completions (disable in prod)
```

### Environment Variables (Override YAML)

```env
TRACING_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
TRACING_SENSITIVE_DATA=true
```

Environment flags take precedence over YAML values.

## Initialization Flow

Early in command execution (`console.py`) we call:

```python
from src.utils.tracing import initialize_tracing
initialize_tracing(config)
```

`initialize_tracing` attempts:

1. `agent_framework.observability.setup_observability(...)`
2. Fallback minimal OTLP exporter (service.name = `dspy-agent-framework`)

Idempotent: subsequent calls are no-ops.

## Sensitive Data Handling

`capture_sensitive` / `TRACING_SENSITIVE_DATA` controls whether prompts & model outputs are included in spans. Recommended:

| Environment | Setting |
| ----------- | ------- |
| Local dev   | true    |
| CI / PR     | false   |
| Production  | false   |

## Viewing Traces

With AI Toolkit: Open the Tracing panel after running a workflow.

External collectors:

- Jaeger: run `jaeger-all-in-one` container and keep default endpoint
- Grafana Tempo: configure OTLP ingestion, update `OTEL_EXPORTER_OTLP_ENDPOINT`
- OpenTelemetry Collector: point to local collector gRPC (4317)

## Disabling Tracing

Set either:

```yaml
tracing:
  enabled: false
```

Or:

```env
TRACING_ENABLED=false
```

No spans are emitted and overhead is removed.

## Testing

`tests/utils/test_tracing.py` ensures initialization is safe with and without dependencies and idempotent.

## Troubleshooting

| Issue                         | Cause                                         | Fix                                                                                                               |
| ----------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| No spans                      | Collector not running                         | Start collector or AI Toolkit tracing panel                                                                       |
| Import error                  | agent-framework version mismatch              | Upgrade `agent-framework` package                                                                                 |
| Prompts missing               | `capture_sensitive` false                     | Set flag true locally                                                                                             |
| High latency                  | Network to remote collector                   | Use local collector or batch processor tuning                                                                     |
| StatusCode.UNAVAILABLE errors | Wrong OTLP port (e.g., 16686 instead of 4317) | Use port **4317** for OTLP/gRPC or **4318** for OTLP/HTTP. Port 16686 is Jaeger's UI, not the collector endpoint. |
| Connection refused            | Collector not started                         | Run `docker ps` to verify Jaeger/collector is running                                                             |

## Security Notes

Disable sensitive data capture in shared/staging/prod environments. Spans may traverse network boundaries.

## Roadmap

- Custom spans around refinement iterations
- Tool invocation semantic attributes (`tool.name`, `tool.latency_ms`)
- Span links between DSPy routing decisions and agent outputs

---

**Need help?** See `README.md` Tracing section or open an issue.
