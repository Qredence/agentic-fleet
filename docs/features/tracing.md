# OpenTelemetry Tracing in AgenticFleet

## Overview

AgenticFleet includes built-in support for distributed tracing using OpenTelemetry via Microsoft Agent Framework's observability module. This automatically instruments all agent operations, chat client calls, and workflow executions.

## Quick Start

### 1. Start AI Toolkit Tracing Viewer

The easiest way to view traces is using VS Code's AI Toolkit extension:

1. Open Command Palette (Cmd+Shift+P / Ctrl+Shift+P)
2. Run: **AI Toolkit: Open Tracing Page**
3. The viewer will start listening on `http://localhost:4317` (gRPC endpoint)

### 2. Run Your Application

Tracing is automatically initialized when you run AgenticFleet:

```bash
# CLI mode - tracing enabled by default
uv run python -m agenticfleet

# Web API mode - tracing enabled by default
make haxui-server
```

### 3. View Traces

Open the AI Toolkit tracing page in VS Code to see real-time traces of:

- Agent executions
- LLM calls (prompts & completions)
- Workflow orchestration
- Tool invocations

## Manual Configuration

### Python Code

```python
from agenticfleet import setup_tracing

# Use defaults (localhost:4317, capture prompts/completions)
setup_tracing()

# Custom configuration
setup_tracing(
    otlp_endpoint="http://jaeger-collector:4317",
    enable_sensitive_data=False  # Disable in production
)

# Check if tracing is active
from agenticfleet import is_tracing_enabled
if is_tracing_enabled():
    print("Tracing is active!")
```

### Environment Variables

Configure tracing without code changes:

```bash
# Disable tracing entirely
export TRACING_ENABLED=false

# Use custom OTLP collector
export OTLP_ENDPOINT=http://jaeger:4317

# Disable sensitive data capture (prompts/completions)
export ENABLE_SENSITIVE_DATA=false
```

## What Gets Traced

The Agent Framework automatically instruments:

### 1. Chat Client Operations

- Model selection and configuration
- Request parameters (temperature, max_tokens, etc.)
- Prompt text (if `enable_sensitive_data=True`)
- Completion text (if `enable_sensitive_data=True`)
- Token usage statistics
- Latency and errors

### 2. Agent Operations

- `agent.run()` and `agent.run_stream()` calls
- Agent initialization and configuration
- Message processing pipeline
- Tool/function calls
- Response generation

### 3. Workflow Execution

- Magentic Fleet orchestration
- Manager planning and evaluation
- Specialist agent delegation
- Progress ledger updates
- Checkpoint creation/restoration

### 4. Workflow-as-Agent Pattern

- Worker response generation
- Reviewer evaluation cycles
- Feedback incorporation
- Approval/rejection decisions

## Trace Visualization

### AI Toolkit Tracing Page

The VS Code AI Toolkit provides a rich UI showing:

- **Waterfall view**: Timeline of operations
- **Span details**: Attributes, events, duration
- **LLM interactions**: Prompts, completions, tokens
- **Error tracking**: Exceptions and stack traces
- **Performance metrics**: Latency percentiles

### Alternative Collectors

You can send traces to any OpenTelemetry-compatible backend:

#### Jaeger

```bash
# Start Jaeger all-in-one
docker run -d --name jaeger \
  -p 4317:4317 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest

# Configure AgenticFleet
export OTLP_ENDPOINT=http://localhost:4317

# View traces at http://localhost:16686
```

#### Zipkin

```bash
# Start Zipkin
docker run -d -p 9411:9411 openzipkin/zipkin

# Use OpenTelemetry collector to forward to Zipkin
# See: https://opentelemetry.io/docs/collector/
```

## Production Considerations

### Security & Privacy

**Disable sensitive data in production:**

```python
setup_tracing(enable_sensitive_data=False)
```

This prevents prompts and LLM completions from being captured in traces, which is important for:

- User privacy (PII in queries)
- Proprietary information protection
- Compliance requirements (GDPR, HIPAA, etc.)

### Performance Impact

Tracing overhead is minimal:

- **CPU**: < 1% additional overhead
- **Memory**: ~10-20 MB for buffering
- **Latency**: < 5ms per span
- **Network**: Async batch export (non-blocking)

### Sampling

For high-traffic production systems, configure sampling:

```python
import os
os.environ["OTEL_TRACES_SAMPLER"] = "traceidratio"
os.environ["OTEL_TRACES_SAMPLER_ARG"] = "0.1"  # Sample 10% of traces
```

## Troubleshooting

### Traces Not Appearing

1. **Check AI Toolkit is running:**

   ```bash
   # Should see "AI Toolkit tracing server started"
   ```

2. **Verify endpoint connectivity:**

   ```bash
   curl http://localhost:4317
   ```

3. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Import Errors

If you see `ImportError: cannot import name 'setup_observability'`:

```bash
# Ensure agent-framework includes OpenTelemetry dependencies
uv pip show agent-framework

# Check version (need agent-framework >= 0.1.0)
uv pip list | grep agent-framework
```

### Disabled Tracing

If tracing is disabled even though you want it enabled:

```bash
# Check environment
echo $TRACING_ENABLED  # Should be empty or "true"
echo $OTLP_ENDPOINT    # Should point to collector

# Remove override if present
unset TRACING_ENABLED
```

## Example Traces

### Simple Agent Query

```
AgenticFleet Query [20ms]
├── Manager Planning [5ms]
│   └── OpenAI Chat Completion [200ms]
│       ├── Model: gpt-4o
│       ├── Prompt: "Research quantum computing"
│       └── Tokens: 150 in, 400 out
├── Researcher Execution [15s]
│   ├── Web Search Tool [1s]
│   └── Response Generation [14s]
│       └── OpenAI Chat Completion [14s]
└── Response Aggregation [5ms]
```

### Workflow-as-Agent with Retry

```
Workflow Agent [8s]
├── Worker: Initial Response [3s]
│   └── OpenAI Chat Completion [3s]
│       └── Model: gpt-4o-mini
├── Reviewer: Evaluation [2s]
│   └── OpenAI Chat Completion [2s]
│       ├── Feedback: "Needs more detail"
│       └── Approved: false
├── Worker: Retry with Feedback [3s]
│   └── OpenAI Chat Completion [3s]
└── Reviewer: Final Approval [2s]
    └── Approved: true
```

## Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Agent Framework Observability](https://github.com/microsoft/agent-framework)
- [AI Toolkit for VS Code](https://marketplace.visualstudio.com/items?itemName=ms-windows-ai-studio.windows-ai-studio)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)

## API Reference

### `setup_tracing()`

```python
def setup_tracing(
    otlp_endpoint: str | None = None,
    enable_sensitive_data: bool = True,
    **kwargs: Any,
) -> None:
    """
    Initialize OpenTelemetry tracing.

    Args:
        otlp_endpoint: OTLP gRPC endpoint (default: http://localhost:4317)
        enable_sensitive_data: Capture prompts/completions (default: True)
        **kwargs: Additional setup_observability arguments
    """
```

### `is_tracing_enabled()`

```python
def is_tracing_enabled() -> bool:
    """Check if tracing is active."""
```

### `get_trace_config()`

```python
def get_trace_config() -> dict[str, Any]:
    """Get current tracing configuration."""
```

## Support

For issues or questions:

- **Agent Framework**: https://github.com/microsoft/agent-framework/issues
- **AgenticFleet**: https://github.com/qredence/agenticfleet/issues
