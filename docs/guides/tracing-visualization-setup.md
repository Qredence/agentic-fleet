# Tracing & Agent Visualization Quick Start

This guide walks you through setting up tracing to visualize the multi-agent workflow execution of AgenticFleet using an OpenTelemetry collector endpoint at `http://localhost:4319`.

## What You'll Get

When tracing is enabled, you can visualize:

- **Agent execution timeline** – See which agents ran, when, and for how long
- **DSPy routing decisions** – Understand how the supervisor routed tasks to agents
- **Tool invocations** – Track tool execution within agents
- **Latency breakdown** – Identify bottlenecks in your workflow
- **Error traces** – Full span details when agents or tools fail

## Prerequisites

- AgenticFleet running locally
- An OpenTelemetry collector listening on `http://localhost:4319` (see "Setting Up the Collector" below)
- Python 3.12+ with the agent-framework package installed

## Quick Setup (3 Steps)

### Step 1: Verify Tracing Configuration in `.env`

Your `.env` file should have these settings:

```env
# Tracing Configuration
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4319
ENABLE_SENSITIVE_DATA=true
```

The updated `.env` already includes these—no changes needed.

**What each setting does:**

- `ENABLE_OTEL=true` – Activates OpenTelemetry tracing
- `OTLP_ENDPOINT=http://localhost:4319` – Sends traces to your local collector (gRPC protocol)
- `ENABLE_SENSITIVE_DATA=true` – Captures prompts & model outputs in traces (disable in production for privacy)

### Step 2: Start an OpenTelemetry Collector

You have two options:

#### Option A: Using Docker (Recommended)

```bash
docker run -d \
  --name otel-collector \
  -p 4319:4317 \
  -p 13133:13133 \
  -p 55679:55679 \
  otel/opentelemetry-collector:latest
```

This runs the OTEL Collector and:

- Accepts OTLP/gRPC traces on port `4317` (mapped to host port `4319`)
- Outputs to stdout (useful for debugging)

#### Option B: Using Jaeger (Includes UI for Visualization)

```bash
docker run -d \
  --name jaeger \
  -p 4319:4317 \
  -p 6831:6831/udp \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest
```

Then view traces in Jaeger UI at: **http://localhost:16686**

**Note:** Jaeger port 16686 is the web UI (read-only). Port 4317 is the OTLP/gRPC collector endpoint.

#### Option C: Using Azure Application Insights (Cloud)

See the [Tracing & Observability Guide](./tracing.md#microsoft-ai-foundry-integration) for production setup with Azure Monitor / AI Foundry.

### Step 3: Start AgenticFleet and Run a Workflow

```bash
# Start the backend (traces will be sent to localhost:4319)
make backend

# In another terminal, run a task via CLI
agentic-fleet run -m "Who is the CEO of Apple?" --verbose

# Or use the web UI
# Visit http://localhost:5173 and chat with the agent
```

## Viewing Your Traces

### If Using Jaeger

1. Open **http://localhost:16686** in your browser
2. Select **`agentic-fleet`** from the Service dropdown
3. Click **Find Traces**
4. You'll see your workflow traces listed with:
   - **Trace ID** – Unique identifier for the entire workflow
   - **Span name** – Individual operations (e.g., `chat_completion`, `routing_decision`)
   - **Duration** – How long each span took
   - **Status** – Success or error

5. Click any trace to expand and see:
   - Nested span hierarchy (parent → child operations)
   - Span attributes (model name, agent name, tool results, etc.)
   - Logs and exceptions
   - Start/end timestamps with precise microsecond resolution

### If Using OTEL Collector Standalone

The collector outputs traces to stdout/logs. For a UI, you'll need to either:

- Connect to **Grafana Tempo** (backend for Grafana)
- Use **Signoz** (open-source APM)
- Push to **Azure Monitor** (cloud option)

## Understanding the Trace Structure

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

Each **span** includes:

- **Attributes**: Context like model name, agent name, tool parameters
- **Events**: Intermediate logging points
- **Duration**: Execution time in milliseconds
- **Status**: OK or ERROR

## Example: Debugging a Slow Workflow

With traces, you can answer questions like:

- _"Why did the analyzer phase take 3 seconds?"_ → Check the `analysis_phase` span duration
- _"Which agent was slowest?"_ → Compare durations across agent execution spans
- _"Did the tool succeed or fail?"_ → Look at the tool invocation span's status
- _"What was the model's output?"_ → If `ENABLE_SENSITIVE_DATA=true`, see prompts/completions in span attributes

## Disabling Traces (When Not Needed)

If you want to disable tracing to reduce overhead:

```env
ENABLE_OTEL=false
```

Then restart the backend. No traces will be emitted, and there's minimal performance impact.

## Common Issues

| Problem                               | Cause                                               | Solution                                                         |
| ------------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------- |
| "Connection refused" / No traces      | Collector not running                               | Run the Docker command from Step 2                               |
| Traces appear in Jaeger but are empty | Missing instrumentation dependencies                | Ensure `agent-framework>=1.0.0b251120` is installed              |
| Can't see prompts/completions         | `ENABLE_SENSITIVE_DATA=false`                       | Set to `true` locally (keep `false` in production)               |
| High latency to collector             | OTLP endpoint is remote or misconfigured            | Use `localhost` endpoint; verify port 4319 is open               |
| "StatusCode.UNAVAILABLE"              | Using wrong OTLP port (e.g., 16686 instead of 4317) | Jaeger UI is port 16686; OTLP/gRPC is port 4317 (mapped to 4319) |

## Architecture Overview

```
AgenticFleet Backend (port 8000)
    ↓ (OTLP/gRPC protocol)
    ↓
OpenTelemetry Collector (port 4319 on host, 4317 in container)
    ├→ Jaeger (port 16686 UI)  ← View traces here
    ├→ Stdout/Logs
    └→ Azure Monitor (optional)
```

## Next Steps

- **[Full Tracing Guide](./tracing.md)** – Comprehensive configuration, Azure Monitor setup, troubleshooting
- **[Agent Architecture](../../developers/architecture.md)** – Understand workflow phases & agent responsibilities
- **[CLI Reference](../../users/getting-started.md#command-line-interface)** – How to run tasks via CLI

## Security Reminder

- `ENABLE_SENSITIVE_DATA=true` captures prompts and model outputs in traces
- **Development**: Keep enabled for debugging
- **Production**: Set to `false` to protect user data and comply with privacy regulations
- Treat OTLP endpoints like any network service—ensure they're only accessible from trusted networks

---

**Ready to debug your agents?** Run `make backend` and watch your workflow traces light up in Jaeger! 🚀
