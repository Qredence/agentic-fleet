# Tracing Status - AgenticFleet

## ✅ Tracing is Fully Implemented

AgenticFleet has **complete OpenTelemetry tracing** integrated using Microsoft Agent Framework's built-in observability.

---

## Current Implementation

### 1. **Core Infrastructure** ✅

The tracing implementation follows Microsoft Agent Framework best practices:

- **Location**: [`src/agentic_fleet/utils/tracing.py`](src/agentic_fleet/utils/tracing.py)
- **Method**: Uses `agent_framework.observability.setup_observability()`
- **Protocol**: gRPC endpoint (recommended by AI Toolkit)
- **Initialization**: Called in [`src/agentic_fleet/main.py`](src/agentic_fleet/main.py#L37) during application startup

### 2. **Environment Configuration** ✅

Current settings in `.env`:

```bash
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4319
ENABLE_SENSITIVE_DATA=true
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
```

**Supported Backends**:

- ✅ Local OTLP/gRPC (Jaeger, AI Toolkit)
- ✅ Azure Monitor / Application Insights
- ✅ VS Code AI Toolkit extension

### 3. **Docker Compose Setup** ✅

**File**: [`docker/docker-compose.tracing.yml`](docker/docker-compose.tracing.yml)

Runs Jaeger with OTLP collector:

- **OTLP gRPC**: `localhost:4319` → `container:4317`
- **Jaeger UI**: `localhost:16686`

### 4. **Make Targets** ✅

```bash
make tracing-start   # Start Jaeger + OTLP collector
make tracing-stop    # Stop tracing collector
```

### 5. **Dependencies** ✅

All required packages are installed:

- `agent-framework>=1.0.0b251211` (includes built-in observability)
- `azure-monitor-opentelemetry>=1.8.3`
- `azure-monitor-opentelemetry-exporter>=1.0.0b46`
- `opentelemetry-exporter-otlp-proto-http>=1.38.0`

---

## How to Use Tracing

### Quick Start (3 Steps)

#### Step 1: Start Tracing Backend

```bash
make tracing-start
```

This starts Jaeger on:

- **UI**: http://localhost:16686 (view traces here)
- **OTLP gRPC**: http://localhost:4319 (receives traces)

#### Step 2: Start AgenticFleet

```bash
make backend
# OR
make dev  # backend + frontend
```

The backend automatically sends traces to the configured endpoint.

#### Step 3: Execute Workflow & View Traces

```bash
# Run a task
agentic-fleet run -m "Who is the CEO of Apple?" --verbose

# OR use the web UI at http://localhost:5173
```

Then open **http://localhost:16686** to see your traces in Jaeger UI.

---

## What Gets Traced

AgenticFleet automatically instruments:

### Agent Framework Operations

- ✅ Chat client calls (OpenAI, Azure OpenAI)
- ✅ Agent executions
- ✅ Tool invocations
- ✅ Workflow phases (analysis → routing → execution → progress → quality)
- ✅ Multi-agent coordination

### Trace Structure

```
Trace: workflow.handle_workflow
├── analysis_phase
│   └── dspy.reasoner.analyze_task
├── routing_phase
│   └── dspy.supervisor.route_agents
├── execution_phase
│   ├── agent.planner.execute
│   ├── agent.researcher.execute
│   └── agent.writer.execute
├── progress_phase
│   └── gepa.progress_check
└── quality_phase
    └── gepa.quality_assessment
```

Each span includes:

- **Duration** (latency)
- **Input/Output** (when `ENABLE_SENSITIVE_DATA=true`)
- **Errors** (if any)
- **Model calls** (tokens, cost estimates)

---

## Configuration Options

### Local Development (Jaeger)

```bash
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4319
ENABLE_SENSITIVE_DATA=true  # Captures prompts/completions
```

### Azure Monitor / AI Foundry

```bash
ENABLE_OTEL=true
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
ENABLE_SENSITIVE_DATA=false  # Recommended for production
```

### VS Code AI Toolkit

```bash
ENABLE_OTEL=true
VS_CODE_EXTENSION_PORT=4317
ENABLE_SENSITIVE_DATA=true
```

### Disable Tracing

```bash
ENABLE_OTEL=false
```

---

## Viewing Traces

### Jaeger UI (Local)

1. Start tracing: `make tracing-start`
2. Open http://localhost:16686
3. Select service: **agentic-fleet**
4. Click **Find Traces**

### Azure Monitor (Production)

1. Set `APPLICATIONINSIGHTS_CONNECTION_STRING` in `.env`
2. View traces in Azure Portal → Application Insights → Transaction Search

### VS Code AI Toolkit

1. Install [AI Toolkit extension](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.vscode-ai-toolkit)
2. Set `VS_CODE_EXTENSION_PORT=4317` in `.env`
3. View traces in VS Code AI Toolkit panel

---

## Troubleshooting

### Traces Not Appearing

**Check 1**: Is tracing enabled?

```bash
grep ENABLE_OTEL .env
# Should show: ENABLE_OTEL=true
```

**Check 2**: Is Jaeger running?

```bash
curl http://localhost:16686
# Should return HTML (Jaeger UI)
```

**Check 3**: Is the backend configured correctly?

```bash
grep OTLP_ENDPOINT .env
# Should show: OTLP_ENDPOINT=http://localhost:4319
```

**Check 4**: Are agent-framework packages installed?

```bash
uv run python -c "from agent_framework.observability import setup_observability; print('✓ OK')"
```

### Common Issues

| Issue                         | Solution                                     |
| ----------------------------- | -------------------------------------------- |
| "Connection refused"          | Run `make tracing-start` to start Jaeger     |
| "No traces found"             | Check `ENABLE_OTEL=true` and restart backend |
| "Module not found"            | Run `make install` to install dependencies   |
| "Sensitive data not captured" | Set `ENABLE_SENSITIVE_DATA=true` in `.env`   |

---

## Documentation

- **Setup Guide**: [`docs/guides/TRACING_SETUP.md`](docs/guides/TRACING_SETUP.md)
- **Quick Reference**: [`docs/guides/TRACING_QUICK_REF.md`](docs/guides/TRACING_QUICK_REF.md)
- **Agent Framework Docs**: https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-observability

---

## Architecture Notes

### Why Agent Framework Observability?

1. **Built-in instrumentation**: Automatically traces all agent/chat operations
2. **Best practices**: Follows Microsoft's official patterns
3. **Multiple backends**: Supports OTLP, Azure Monitor, VS Code
4. **Zero manual spans**: No need to create spans manually

### Code Implementation

```python
# src/agentic_fleet/utils/tracing.py
from agent_framework.observability import setup_observability

setup_observability(
    otlp_endpoint="http://localhost:4319",  # gRPC endpoint (AI Toolkit compatible)
    enable_sensitive_data=True  # Capture prompts/completions
)
```

### Initialization Flow

1. **Environment Check**: Read `ENABLE_OTEL` flag
2. **Config Resolution**: Merge env vars + config YAML
3. **Setup Call**: Invoke `setup_observability()` with resolved config
4. **Global Provider**: Agent Framework configures OpenTelemetry globally
5. **Auto-Instrumentation**: All subsequent agent/workflow operations are traced

---

## Next Steps

### ✅ Already Complete

- [x] Core tracing implementation
- [x] Environment configuration
- [x] Docker compose for Jaeger
- [x] Make targets for easy startup
- [x] Documentation

### Optional Enhancements

- [ ] **Custom Metrics**: Add application-specific metrics using `get_meter()`
- [ ] **Custom Spans**: Add manual spans for business logic using `get_tracer()`
- [ ] **Production Deployment**: Configure Azure Monitor for cloud tracing
- [ ] **Alerting**: Set up alerts in Azure Monitor for errors/latency

---

## Summary

✅ **Tracing is fully implemented and ready to use!**

To start using it:

```bash
make tracing-start    # Start Jaeger
make backend          # Start backend (sends traces automatically)
# Open http://localhost:16686 to view traces
```

All tracing infrastructure follows Microsoft Agent Framework best practices and is production-ready.
