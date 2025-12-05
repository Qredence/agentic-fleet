# Tracing & Observability Guide

This guide explains how to enable, configure, and use tracing for AgenticFleet.

## Overview

Tracing provides deep visibility into multi-agent workflow execution. Using the **agent-framework**'s built-in OpenTelemetry instrumentation you automatically get spans for:

- Agent creation & lifecycle
- Chat client requests (prompt + completion latency)
- DSPy compilation (BootstrapFewShot / GEPA) when enabled
- Workflow phases (routing, execution, refinement)
- Tool invocations (when instrumented by underlying SDK)

If the agent-framework observability helper is unavailable the framework falls back to manual OpenTelemetry setup.

## Export Destinations

AgenticFleet supports multiple trace export destinations:

| Destination              | Use Case                   | Configuration                          |
| ------------------------ | -------------------------- | -------------------------------------- |
| **AI Toolkit**           | Local development          | `otlp_endpoint: http://localhost:4317` |
| **Microsoft AI Foundry** | Production monitoring      | `azure_monitor_connection_string`      |
| **Jaeger**               | Self-hosted tracing        | `otlp_endpoint: http://jaeger:4317`    |
| **Grafana Tempo**        | Cloud-native observability | Custom OTLP endpoint                   |

## Configuration Methods

### YAML (Preferred)

Add a `tracing` section to `config/workflow_config.yaml`:

```yaml
tracing:
  enabled: true
  otlp_endpoint: http://localhost:4317 # OTLP gRPC port (NOT 16686 which is Jaeger UI)
  capture_sensitive: true # Export prompts & completions (disable in prod)
  # Azure Monitor / AI Foundry export (optional)
  azure_monitor_connection_string: # Your Application Insights connection string
```

### Environment Variables (Override YAML)

```env
TRACING_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
TRACING_SENSITIVE_DATA=true

# Azure Monitor / AI Foundry
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx;IngestionEndpoint=https://xxx.applicationinsights.azure.com/
```

Environment flags take precedence over YAML values.

## Microsoft AI Foundry Integration

To export traces to Microsoft AI Foundry for production monitoring:

### 1. Install the tracing extra

```bash
uv add agentic-fleet[tracing]
# or
pip install azure-monitor-opentelemetry
```

### 2. Get your Application Insights connection string

1. Navigate to **Tracing** in the left navigation pane of the Foundry portal
2. Create a new Application Insights resource if you don't already have one
3. Connect the resource to your Foundry project
4. Go to **Manage data source** > **Connection string**

### 3. Configure the connection string

**Option A: Environment variable (recommended for production)**

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx;IngestionEndpoint=https://xxx.applicationinsights.azure.com/"
```

**Option B: YAML configuration**

```yaml
tracing:
  enabled: true
  azure_monitor_connection_string: "InstrumentationKey=xxx;IngestionEndpoint=https://xxx.applicationinsights.azure.com/"
  capture_sensitive: false # IMPORTANT: Set to false in production!
```

### 4. View traces in Foundry

After running your agents:

1. Go to your AI Foundry project
2. Navigate to **Tracing** in the left panel
3. Filter and explore your traces
4. Click on individual traces to see detailed spans

### Programmatic access to connection string

If you're using the Azure AI Projects SDK, you can retrieve the connection string programmatically:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project_client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=os.environ["PROJECT_ENDPOINT"],
)

connection_string = project_client.telemetry.get_application_insights_connection_string()
```

## Initialization Flow

Early in command execution (`src/agentic_fleet/cli/console.py`) we call:

```python
from src.agentic_fleet.utils.tracing import initialize_tracing
initialize_tracing(config)
```

`initialize_tracing` attempts (in order):

1. Azure Monitor export (if connection string is set)
2. `agent_framework.observability.setup_observability(...)`
3. Fallback minimal OTLP exporter (service.name = `agentic-fleet`)

Idempotent: subsequent calls are no-ops.

## Sensitive Data Handling

`capture_sensitive` / `TRACING_SENSITIVE_DATA` controls whether prompts & model outputs are included in spans.

| Environment | Setting | Reason                      |
| ----------- | ------- | --------------------------- |
| Local dev   | true    | Full debugging visibility   |
| CI / PR     | false   | Avoid logging secrets in CI |
| Production  | false   | GDPR/privacy compliance     |

**⚠️ Warning**: When using Azure Monitor in production, always set `capture_sensitive: false` to avoid sending PII/sensitive data to Application Insights.

## Viewing Traces

### AI Toolkit (Local Development)

1. Open VS Code
2. Go to AI Toolkit panel
3. Click "Tracing" in the tree view
4. Click "Start Collector"
5. Run your workflow
6. Refresh to see traces

### Microsoft AI Foundry (Production)

1. Navigate to your project in the Foundry portal
2. Click **Tracing** in the left navigation
3. Use filters to find specific traces
4. Click on a trace to see the span hierarchy

### Azure Monitor / Application Insights

For deeper analysis:

1. Open Azure Portal
2. Navigate to your Application Insights resource
3. Use **End-to-end transaction details view** for investigation

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
| Azure Monitor not working     | Missing dependency                            | Install with `uv add agentic-fleet[tracing]` or `pip install azure-monitor-opentelemetry`                         |
| No traces in Foundry          | Invalid connection string                     | Verify connection string from Foundry portal > Tracing > Manage data source                                       |

## Security Notes

- Disable sensitive data capture in shared/staging/prod environments
- Spans may traverse network boundaries
- Azure Monitor connection strings should be treated as secrets
- Use managed identity where possible for Azure authentication

## Roadmap

- Custom spans around refinement iterations
- Tool invocation semantic attributes (`tool.name`, `tool.latency_ms`)
- Span links between DSPy routing decisions and agent outputs
- Dual export (local + Azure Monitor simultaneously)

---

**Need help?** See `README.md` Tracing section or open an issue.
