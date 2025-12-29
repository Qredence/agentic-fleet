# Tracing & Observability Guide

This guide explains how to enable, configure, and use tracing for AgenticFleet. It combines quick-start instructions for local development with advanced configuration for production monitoring.

## Overview

Tracing provides deep visibility into multi-agent workflow execution. Using the **agent-framework**'s built-in OpenTelemetry instrumentation you automatically get spans for:

- **Agent execution timeline** – See which agents ran, when, and for how long
- **DSPy routing decisions** – Understand how the supervisor routed tasks to agents
- **Tool invocations** – Track tool execution within agents
- **Latency breakdown** – Identify bottlenecks in your workflow
- **Error traces** – Full span details when agents or tools fail

## 🚀 Quick Start (Local Development)

Visualizing your agents takes just 3 commands.

### 1. Start the Tracing Collector

```bash
make tracing-start
```

This starts a local Jaeger instance with an OpenTelemetry collector:

- **UI**: http://localhost:16686 (View traces)
- **Endpoint**: http://localhost:4319 (Send traces via OTLP/gRPC)

### 2. Start the Backend

```bash
make backend
```

The backend automatically detects the local collector and begins sending traces.

### 3. Run a Workflow

```bash
# Run a task via CLI
agentic-fleet run -m "Who is the CEO of Apple?" --verbose

# OR use the web UI at http://localhost:5173
```

Then open **http://localhost:16686** to see your traces!

---

## Configuration

Tracing is configured via `src/agentic_fleet/config/workflow_config.yaml` or environment variables (which take precedence).

### Standard Configuration

```yaml
tracing:
  enabled: true
  otlp_endpoint: http://localhost:4319 # OTLP gRPC port
  capture_sensitive: true # Export prompts & completions (disable in prod)
```

### Environment Variables

```env
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4319
ENABLE_SENSITIVE_DATA=true
```

### Sensitive Data Handling

`capture_sensitive` / `ENABLE_SENSITIVE_DATA` controls whether prompts & model outputs are included in spans.

| Environment | Setting | Reason                      |
| ----------- | ------- | --------------------------- |
| Local dev   | `true`  | Full debugging visibility   |
| CI / PR     | `false` | Avoid logging secrets in CI |
| Production  | `false` | GDPR/privacy compliance     |

**⚠️ Warning**: When using Azure Monitor in production, always set `capture_sensitive: false` to avoid sending PII/sensitive data to Application Insights.

---

## Viewing Traces in Jaeger

1. Open **http://localhost:16686**
2. Select **`agentic-fleet`** from the **Service** dropdown
3. Click **Find Traces**

### Understanding the Trace Structure

A typical AgenticFleet trace looks like:

```
Trace: handle_workflow
├── Span: analysis_phase
│   ├── Span: decompose_task (DSPy module)
│   └── Span: chat_completion (OpenAI API)
├── Span: routing_phase
│   ├── Span: routing_decision (DSPy module)
│   └── Span: select_agents (DSPy module)
├── Span: execution_phase
│   ├── Span: agent_1_execution
│   │   ├── Span: tool_invocation (e.g., web_search)
│   │   └── Span: chat_completion
│   ├── Span: agent_2_execution
│   └── ...
├── Span: quality_phase
│   └── Span: quality_assessment (DSPy module)
└── Span: final_response
```

---

## Export Destinations

AgenticFleet supports multiple trace export destinations:

| Destination              | Use Case                   | Configuration                          |
| ------------------------ | -------------------------- | -------------------------------------- |
| **Jaeger (Local)**       | Development                | `otlp_endpoint: http://localhost:4319` |
| **Microsoft AI Foundry** | Production monitoring      | `azure_monitor_connection_string`      |
| **Grafana Tempo**        | Cloud-native observability | Custom OTLP endpoint                   |

### Microsoft AI Foundry Integration

To export traces to Microsoft AI Foundry for production monitoring:

1.  **Install dependencies**:

    ```bash
    uv add agentic-fleet[tracing]
    # or
    pip install azure-monitor-opentelemetry
    ```

2.  **Configure Connection String**:

    ```bash
    export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx;IngestionEndpoint=https://xxx.applicationinsights.azure.com/"
    ```

    Or in `workflow_config.yaml`:

    ```yaml
    tracing:
      enabled: true
      azure_monitor_connection_string: "..."
      capture_sensitive: false # Important for production
    ```

3.  **View Traces**: Navigate to the **Tracing** tab in your AI Foundry project.

---

## Troubleshooting

| Issue                         | Cause                            | Fix                                                                 |
| ----------------------------- | -------------------------------- | ------------------------------------------------------------------- |
| **No traces showing**         | Collector not running            | Run `make tracing-start`                                            |
| **Connection refused**        | Backend started before collector | Restart backend after starting tracing                              |
| **Prompts missing**           | `capture_sensitive` is false     | Set `ENABLE_SENSITIVE_DATA=true` in `.env`                          |
| **StatusCode.UNAVAILABLE**    | Wrong OTLP port                  | Use port **4319** (mapped to container 4317). Port 16686 is the UI. |
| **Azure Monitor not working** | Missing dependency               | Install with `uv add agentic-fleet[tracing]`                        |

## Disabling Tracing

To completely disable tracing overhead:

```env
ENABLE_OTEL=false
```
