# Tracing Setup Summary

## ✅ Changes Made

You now have a complete setup for visualizing your multi-agent workflow with OpenTelemetry tracing and Jaeger UI at `http://localhost:4319`.

### 1. **Environment Configuration Updated**

- **File**: `.env`
- **Changes**: Updated tracing variables to use the OTLP endpoint at `http://localhost:4319`
- **Settings**:
  ```env
  ENABLE_OTEL=true
  OTLP_ENDPOINT=http://localhost:4319
  ENABLE_SENSITIVE_DATA=true
  ```

### 2. **Docker Compose for Easy Setup**

- **File**: `docker-compose.tracing.yml`
- **Purpose**: Runs Jaeger with OTLP collector in one command
- **Usage**: `make tracing-start`

### 3. **Convenience Scripts**

- **Start tracing**: `scripts/start_tracing.sh` (also accessible via `make tracing-start`)
- **Stop tracing**: `scripts/stop_tracing.sh` (also accessible via `make tracing-stop`)
- Both scripts handle Docker setup automatically

### 4. **Makefile Targets Added**

```makefile
make tracing-start    # Start OpenTelemetry collector + Jaeger UI
make tracing-stop     # Stop the collector
```

### 5. **Documentation**

- **Quick Start Guide**: `docs/guides/tracing-visualization-setup.md`
- Explains how to:
  - Understand trace structure
  - Debug workflow performance
  - View traces in Jaeger UI
  - Handle common issues

---

## 🚀 Quick Start (3 Commands)

### Step 1: Start the Tracing Collector

```bash
make tracing-start
```

This will:

- Start Jaeger container on port 16686 (UI) and 4319 (OTLP endpoint)
- Verify the collector is ready
- Print instructions

### Step 2: Start the Backend

```bash
make backend
```

This will:

- Start AgenticFleet on http://localhost:8000
- Automatically send traces to http://localhost:4319

### Step 3: Run a Workflow and View Traces

```bash
# Run a task via CLI
agentic-fleet run -m "Who is the CEO of Apple?" --verbose

# OR use the web UI
# Visit http://localhost:5173 and chat
```

Then open **http://localhost:16686** to see your traces!

---

## 📊 What You Can See in Jaeger

Once you run a workflow, Jaeger will show you:

1. **Service**: Select `agentic-fleet` from dropdown
2. **Trace timeline**: See the entire workflow execution
3. **Span details**:
   - Agent execution durations
   - Tool invocation results
   - Model response latencies
   - Error details if something fails

Example trace structure:

```
Trace: handle_workflow
├── analysis_phase (time to analyze task)
├── routing_phase (time to decide which agents)
├── execution_phase (parallel/sequential agent execution)
├── quality_phase (refinement if needed)
└── final_response (total latency)
```

---

## 🔧 Configuration Options

All settings are in `.env`:

| Setting                 | Value                   | Purpose                                            |
| ----------------------- | ----------------------- | -------------------------------------------------- |
| `ENABLE_OTEL`           | `true`                  | Master switch for tracing                          |
| `OTLP_ENDPOINT`         | `http://localhost:4319` | Where to send traces (gRPC)                        |
| `ENABLE_SENSITIVE_DATA` | `true`                  | Capture prompts/outputs in traces (local dev only) |

### To Disable Tracing

```env
ENABLE_OTEL=false
```

---

## 📖 Learn More

- **Full tracing guide**: `docs/guides/tracing.md`
- **Quick reference**: `docs/guides/tracing-visualization-setup.md`
- **Architecture**: `docs/developers/architecture.md`

---

## 🛑 Stopping Everything

```bash
# Stop tracing collector
make tracing-stop

# Stop backend
# Ctrl+C in the backend terminal
```

---

## ⚠️ Important Notes

1. **Sensitive data**: `ENABLE_SENSITIVE_DATA=true` captures prompts and model outputs
   - ✅ Use in local development
   - ❌ Disable in production for privacy

2. **Port mapping**:
   - Jaeger UI: http://localhost:16686 (view traces here)
   - OTLP gRPC: http://localhost:4319 (backend sends traces here)
   - Do NOT use 16686 as the OTLP endpoint—it's the UI only

3. **Persistence**: Traces persist in Docker between restarts
   - Restart with `make tracing-start` to see historical traces

---

## 🎯 Next Steps

1. ✅ Configuration is ready (OTLP endpoint set to localhost:4319)
2. Run `make tracing-start` to launch Jaeger
3. Run `make backend` to start AgenticFleet
4. Execute a workflow: `agentic-fleet run -m "Your task"`
5. Open http://localhost:16686 and select `agentic-fleet` service
6. Click "Find Traces" to see your workflow traces

Happy debugging! 🚀
