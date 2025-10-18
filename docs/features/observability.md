# OpenTelemetry Observability

**Status**: ✅ Available (v0.5.2+)
**Last Updated**: October 17, 2025

## Overview

AgenticFleet includes built-in OpenTelemetry tracing support via the Microsoft Agent Framework. This provides comprehensive visibility into:

- Workflow orchestration and planning
- Agent-to-agent interactions
- LLM API calls (prompts and completions)
- Tool executions
- Performance metrics and bottlenecks

## Quick Start

### 1. Enable Tracing

Edit your `.env` file:

```bash
# Enable OpenTelemetry tracing
ENABLE_OTEL=true

# Capture prompts and completions (optional, useful for debugging)
ENABLE_SENSITIVE_DATA=true

# OpenTelemetry collector endpoint (default: localhost:4317)
OTLP_ENDPOINT="http://localhost:4317"
```

### 2. Start a Collector

**Option A: Jaeger (Recommended)**

```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest
```

Then open the Jaeger UI at: **http://localhost:16686**

**Option B: OpenTelemetry Collector**

```bash
docker run -d --name otel-collector \
  -p 4317:4317 \
  -p 55679:55679 \
  otel/opentelemetry-collector:latest
```

**Option C: AI Toolkit (VS Code)**

If you have AI Toolkit installed in VS Code, it provides a built-in tracing UI accessible via Command Palette → "AI Toolkit: Open Tracing".

### 3. Run Your Application

```bash
uv run fleet
```

You'll see a confirmation message:

```text
Notice
________________________________________________________________________
  OpenTelemetry tracing enabled
```

All workflow operations will now be traced and exported to your collector.

## What Gets Traced

The Agent Framework automatically instruments:

### Workflow Operations

- **`workflow.build`** - Workflow graph construction
- **`workflow.run`** - Complete workflow execution
- **`executor.execute`** - Individual executor steps

### Agent Operations

- **`agent.process`** - Agent message processing
- **`magentic.plan`** - Manager planning operations
- **`magentic.evaluate`** - Progress ledger evaluation
- **Agent delegation** - Routing between agents

### LLM Interactions

- **Model calls** - Complete request/response pairs
- **Token usage** - Input and output token counts
- **Latency** - Time per LLM call
- **Prompts & completions** - Full content (when `ENABLE_SENSITIVE_DATA=true`)

### Tool Executions

- **Tool calls** - Each tool invocation
- **Parameters** - Tool input arguments
- **Results** - Tool output data
- **Errors** - Tool execution failures

## Viewing Traces

### Jaeger UI

1. Open **http://localhost:16686**
2. Select **Service**: `agent_framework`
3. Click **Find Traces**
4. Click any trace to see:
   - Complete span hierarchy
   - Timing information
   - Agent interactions
   - LLM calls with prompts/responses
   - Performance bottlenecks

### Key Metrics to Monitor

- **Workflow duration** - Total execution time
- **Agent response time** - Time per agent turn
- **LLM latency** - API call performance
- **Tool execution time** - Tool performance
- **Error rates** - Failed operations

## Configuration Reference

### Environment Variables

| Variable                | Default                 | Description                     |
| ----------------------- | ----------------------- | ------------------------------- |
| `ENABLE_OTEL`           | `false`                 | Enable OpenTelemetry tracing    |
| `ENABLE_SENSITIVE_DATA` | `false`                 | Capture prompts and completions |
| `OTLP_ENDPOINT`         | `http://localhost:4317` | gRPC endpoint for OTLP exporter |

### Settings API

The observability settings are loaded in `src/agenticfleet/config/settings.py`:

```python
from agenticfleet.config import settings

# Check if tracing is enabled
if settings.enable_otel:
    print(f"Tracing to: {settings.otlp_endpoint}")
    print(f"Sensitive data: {settings.enable_sensitive_data}")
```

## Architecture

### Implementation

The tracing setup is initialized in `src/agenticfleet/cli/repl.py`:

```python
# Set up OpenTelemetry tracing if enabled
if settings.enable_otel:
    try:
        from agent_framework.observability import setup_observability
        setup_observability(
            otlp_endpoint=settings.otlp_endpoint,
            enable_sensitive_data=settings.enable_sensitive_data
        )
        ui.log_notice("OpenTelemetry tracing enabled")
    except ImportError:
        ui.log_notice("agent_framework observability not available", style="yellow")
```

### Instrumentation

The Agent Framework provides automatic instrumentation via the `setup_observability()` function. No manual span creation is required—all operations are traced automatically.

### Export Protocol

- **Protocol**: gRPC (OTLP)
- **Endpoint**: Configurable via `OTLP_ENDPOINT`
- **Format**: OpenTelemetry Protocol (OTLP)
- **Compression**: Enabled by default

## Troubleshooting

### No Traces Appearing

1. **Check collector is running**:

   ```bash
   docker ps | grep jaeger
   # or
   lsof -i :4317
   ```

2. **Verify environment variables**:

   ```bash
   uv run python -c "from agenticfleet.config import settings; \
     print(f'ENABLE_OTEL: {settings.enable_otel}'); \
     print(f'OTLP_ENDPOINT: {settings.otlp_endpoint}')"
   ```

3. **Check for errors in logs**:
   ```bash
   tail -f var/logs/agenticfleet.log | grep -i otel
   ```

### Connection Errors

If you see `StatusCode.UNAVAILABLE` errors:

1. Ensure the collector is running on the correct port
2. Check firewall settings
3. Verify the endpoint URL format (should include protocol: `http://`)

### Disable Tracing

Set `ENABLE_OTEL=false` in your `.env` file to disable tracing completely.

## Production Considerations

### Security

- **Sensitive data**: Only enable `ENABLE_SENSITIVE_DATA=true` in development
- **API keys**: Prompts may contain API keys if enabled
- **PII**: User data will be captured in traces

### Performance

- **Overhead**: Minimal (<5% typical overhead)
- **Sampling**: Consider sampling in high-volume production
- **Network**: Traces are sent asynchronously to minimize impact

### Storage

- **Retention**: Configure Jaeger/collector retention policies
- **Volume**: Expect ~1-5KB per trace depending on complexity
- **Cleanup**: Set up automated cleanup for old traces

## Advanced Configuration

### Custom Collector Configuration

For production deployments, use a custom collector configuration:

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  jaeger:
    endpoint: jaeger:14250
  prometheus:
    endpoint: 0.0.0.0:9090

processors:
  batch:
    timeout: 10s

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
```

### Integration with Monitoring Platforms

AgenticFleet tracing integrates with:

- **Jaeger** - Distributed tracing
- **Zipkin** - Alternative trace viewer
- **Prometheus** - Metrics collection
- **Grafana** - Visualization and dashboards
- **Azure Application Insights** - Cloud monitoring (set `APPLICATIONINSIGHTS_CONNECTION_STRING`)

## Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Agent Framework Observability](https://github.com/microsoft/agent-framework)
- [AI Toolkit for VS Code](https://marketplace.visualstudio.com/items?itemName=ms-windows-ai-studio.windows-ai-studio)

## Related Documentation

- [`../operations/developer-environment.md`](../operations/developer-environment.md) - Development setup
- [`../architecture/magentic-fleet.md`](../architecture/magentic-fleet.md) - Workflow architecture
- [`../getting-started/quick-reference.md`](../getting-started/quick-reference.md) - Quick start guide
