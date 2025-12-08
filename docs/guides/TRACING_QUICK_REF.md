# 📊 Tracing & Visualization - Quick Reference Card

## One-Minute Setup

```bash
# 1. Start tracing collector (Jaeger UI at http://localhost:16686)
make tracing-start

# 2. In another terminal, start backend
make backend

# 3. Run a workflow
agentic-fleet run -m "Your task here" --verbose

# 4. View traces
# Open http://localhost:16686 → Select "agentic-fleet" → Find Traces
```

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│ AgenticFleet Backend (port 8000)                        │
│ • Sends OpenTelemetry traces                           │
└──────────────────┬──────────────────────────────────────┘
                   │ OTLP/gRPC
                   ↓ http://localhost:4319
┌─────────────────────────────────────────────────────────┐
│ Jaeger Container                                         │
│ • Collects traces (port 4317 inside container)         │
│ • Web UI at http://localhost:16686                     │
└─────────────────────────────────────────────────────────┘
```

---

## What You See in Jaeger

### 1. **Service List**

- Dropdown at top left
- Select: `agentic-fleet`

### 2. **Trace View**

Shows all traces with:

- **Trace ID**: Unique identifier for a workflow run
- **Spans**: Individual operations (analysis, routing, execution, etc.)
- **Duration**: How long the trace took
- **Status**: Success ✓ or Error ✗

### 3. **Click a Trace to See**

```
handle_workflow (2.5s)
├── analysis_phase (0.8s)
│   └── decompose_task
├── routing_phase (0.4s)
│   └── routing_decision
├── execution_phase (1.0s)
│   ├── agent_1_execution
│   └── agent_2_execution
├── quality_phase (0.2s)
└── final_response
```

---

## Configuration

### Enable/Disable Tracing

**Enable** (development):

```env
ENABLE_OTEL=true
OTLP_ENDPOINT=http://localhost:4319
ENABLE_SENSITIVE_DATA=true  # Captures prompts/outputs
```

**Disable** (when not needed):

```env
ENABLE_OTEL=false
```

### Other Options

```env
# Capture sensitive data (prompts, responses)
# ✅ Local dev  | ❌ Production
ENABLE_SENSITIVE_DATA=true

# Alternative endpoints (for cloud/production)
APPLICATIONINSIGHTS_CONNECTION_STRING=<...>  # Azure Monitor
```

---

## Common Tasks

### Debug Workflow Latency

1. Open Jaeger → Find Traces
2. Click the slow trace
3. Expand each span to see which phase is slow
4. Look at span attributes (model, agent name, etc.)

### Check Tool Execution

1. Find trace in Jaeger
2. Look for spans named `tool_invocation` or `web_search`
3. Check span status and attributes for results

### View Model Prompts (if `ENABLE_SENSITIVE_DATA=true`)

1. Click a trace
2. Find span for `chat_completion`
3. View span attributes (should include prompt)

### Find Errors

1. Jaeger → Filter by status: `error`
2. Click trace
3. Look for red spans (failed operations)
4. Check span logs/events for error messages

---

## Useful Jaeger Features

| Feature                | How to Use                                          |
| ---------------------- | --------------------------------------------------- |
| **Filter by service**  | Dropdown at top left → `agentic-fleet`              |
| **Filter by status**   | Use filter bar (e.g., `status:error`)               |
| **Filter by duration** | Search params: `minDuration:1s` or `maxDuration:5s` |
| **Compare traces**     | Click multiple traces with Ctrl/Cmd, see diff       |
| **Export trace**       | Click trace → "Copy trace ID" or "Download JSON"    |

---

## Troubleshooting

| Problem              | Fix                                                |
| -------------------- | -------------------------------------------------- |
| "Connection refused" | Run `make tracing-start` first                     |
| No traces appear     | Check `ENABLE_OTEL=true` in .env                   |
| Can't see prompts    | Set `ENABLE_SENSITIVE_DATA=true`                   |
| Wrong service name   | Make sure you selected `agentic-fleet` in dropdown |
| Jaeger UI is slow    | Close extra tabs; Jaeger UI is heavy               |

---

## Files Reference

| File                                         | Purpose                                                    |
| -------------------------------------------- | ---------------------------------------------------------- |
| `.env`                                       | Tracing configuration (OTLP endpoint, sensitive data flag) |
| `docker-compose.tracing.yml`                 | Docker setup for Jaeger                                    |
| `scripts/start_tracing.sh`                   | Launch Jaeger (runs `make tracing-start`)                  |
| `scripts/stop_tracing.sh`                    | Stop Jaeger (runs `make tracing-stop`)                     |
| `docs/guides/tracing.md`                     | Full tracing documentation                                 |
| `docs/guides/tracing-visualization-setup.md` | Setup & visualization guide                                |

---

## Command Cheat Sheet

```bash
# Start/Stop
make tracing-start     # Launch Jaeger + collector
make tracing-stop      # Stop collector

# View
make backend           # Start backend (sends traces to port 4319)
make dev              # Start backend + frontend

# Run Tasks
agentic-fleet run -m "task" --verbose
# Then: Open http://localhost:16686

# Inspect
# Use Jaeger UI to filter, search, and analyze traces
```

---

## Next Steps

✅ **Tracing is ready!** Your `.env` is configured with:

- OTLP endpoint: `http://localhost:4319`
- Sensitive data capture: `true` (for local dev)

👉 **Next**: Run `make tracing-start` to launch Jaeger!

---

_For detailed info, see `docs/guides/tracing-visualization-setup.md`_
