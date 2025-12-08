# Tracing & Observability - Documentation Index

## 🎯 Start Here

Choose based on your needs:

### **I want to visualize my agents RIGHT NOW** →

→ [**TRACING_QUICK_REF.md**](./TRACING_QUICK_REF.md) (2-min read)

### **I want detailed setup + troubleshooting** →

→ [**tracing-visualization-setup.md**](./tracing-visualization-setup.md) (10-min read)

### **I want comprehensive tracing docs** →

→ [**tracing.md**](./tracing.md) (reference)

---

## 📚 All Tracing Guides

| Document                                                               | Length    | Use Case                                           |
| ---------------------------------------------------------------------- | --------- | -------------------------------------------------- |
| [**TRACING_QUICK_REF.md**](./TRACING_QUICK_REF.md)                     | 2 min     | Quick reference card, one-liner commands           |
| [**TRACING_SETUP.md**](./TRACING_SETUP.md)                             | 5 min     | Summary of what's been configured for you          |
| [**tracing-visualization-setup.md**](./tracing-visualization-setup.md) | 10 min    | Full setup guide + how to use Jaeger               |
| [**tracing.md**](./tracing.md)                                         | Reference | Comprehensive reference (all options, cloud setup) |

---

## 🚀 The 30-Second Version

```bash
make tracing-start    # Start Jaeger UI
make backend          # Start backend (sends traces to localhost:4319)
agentic-fleet run -m "Who is the CEO of Apple?"  # Run a task
# Open http://localhost:16686 → select agentic-fleet → see traces!
```

---

## 🔍 How Tracing Works in AgenticFleet

1. **Backend** (Python) uses OpenTelemetry to create spans for:
   - Agent analysis phase
   - Routing decisions
   - Tool executions
   - Model API calls

2. **Spans are sent** via gRPC to OTLP endpoint (`http://localhost:4319`)

3. **Collector** (Jaeger) receives and stores traces

4. **Jaeger UI** (http://localhost:16686) displays traces in a timeline

### Typical Workflow Trace

```
├── Analysis: Decompose the task (0.8s)
├── Routing: Decide which agents to use (0.4s)
├── Execution: Run agents in parallel (1.0s)
│  ├── Agent 1: Research
│  └── Agent 2: Analysis
├── Quality: Verify results (0.2s)
└── Total: 2.4s
```

---

## 📋 What's Already Been Set Up For You

✅ **Configuration** (`.env`)

- OTLP endpoint: `http://localhost:4319`
- Sensitive data capture: enabled (for local dev)

✅ **Docker Setup** (`docker-compose.tracing.yml`)

- One-command Jaeger launch

✅ **Scripts**

- `scripts/start_tracing.sh` → `make tracing-start`
- `scripts/stop_tracing.sh` → `make tracing-stop`

✅ **Documentation** (you're reading it!)

- This index
- Quick reference
- Full setup guide

---

## 🎯 Common Tasks

### See Which Phase Is Slow

1. Open http://localhost:16686
2. Find trace for your workflow
3. Expand timeline—each color bar is a phase
4. Click phase to see details

### Debug a Tool Failure

1. In Jaeger, filter for error traces
2. Find the red span (failed operation)
3. Check span attributes and logs for error message

### Compare Two Runs

1. Run workflow twice
2. In Jaeger, click both traces while holding Ctrl/Cmd
3. See side-by-side comparison

### Export Trace Data

1. Click trace → "Copy Trace ID"
2. Or download as JSON from browser dev tools

---

## 🔧 Configuration Reference

### Current Setup

```env
ENABLE_OTEL=true                           # Tracing enabled
OTLP_ENDPOINT=http://localhost:4319       # Where backend sends traces
ENABLE_SENSITIVE_DATA=true                # Capture prompts/outputs (dev only)
```

### To Disable

```env
ENABLE_OTEL=false
```

### For Production (Azure Monitor)

See **[tracing.md](./tracing.md)** section "Microsoft AI Foundry Integration"

---

## 🛠️ Useful Commands

```bash
# Start everything
make tracing-start    # Jaeger
make backend          # Backend

# Useful workflow
agentic-fleet run -m "task" --verbose

# Cleanup
make tracing-stop     # Stop collector
make clear-cache      # Clear DSPy cache if needed
```

---

## 📞 Need Help?

| Issue                | Solution                                              |
| -------------------- | ----------------------------------------------------- |
| No traces showing    | `ENABLE_OTEL=true` in .env? Run `make tracing-start`? |
| Can't see prompts    | Set `ENABLE_SENSITIVE_DATA=true` (already done)       |
| Wrong OTLP port      | Use port 4319 (or 4317 if not containerized)          |
| High latency         | Check network, reduce sample rate if needed           |
| Missing dependencies | `uv sync` to reinstall                                |

See **[tracing-visualization-setup.md](./tracing-visualization-setup.md#common-issues)** for more troubleshooting.

---

## 📖 Related Docs

- **[Architecture Guide](../developers/architecture.md)** – Understand workflow phases
- **[Getting Started](../users/getting-started.md)** – Run your first workflow
- **[CLI Reference](../users/getting-started.md#command-line-interface)** – All CLI commands

---

## ✨ Next Step

👉 **Run `make tracing-start` and open http://localhost:16686** ✨
