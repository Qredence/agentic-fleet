---
title: '[OPT-05] Implement Proper Observability with OpenTelemetry'
labels: ['enhancement', 'optimization', 'observability', 'monitoring']
---

## Priority Level
🟡 **Medium Priority** - Operational Insights

## Overview
Enhance observability by implementing proper OpenTelemetry integration for distributed tracing, metrics collection, and performance monitoring across all agents and workflows.

## Current State

### Implementation
- Basic logging setup in `src/agenticfleet/core/logging.py`
- File-based logs in `logs/agenticfleet.log`
- No distributed tracing
- Limited metrics collection
- No cost tracking per agent

### Limitations
- Cannot trace requests across multiple agents
- No visibility into LLM token usage and costs
- Difficult to identify performance bottlenecks
- No production monitoring capabilities
- Manual log parsing for debugging

## Proposed Implementation

```python
# File: src/agenticfleet/core/observability.py
from agent_framework.observability import enable_tracing
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

def setup_observability():
    """Configure OpenTelemetry for AgenticFleet."""
    
    # Enable agent framework tracing
    enable_tracing(
        service_name="agenticfleet",
        service_version="0.6.0",
        exporter=OTLPSpanExporter(
            endpoint=settings.otel_endpoint or "http://localhost:4317",
            insecure=settings.otel_insecure,
        ),
    )
    
    # Configure metrics
    metrics.set_meter_provider(
        MeterProvider(
            metric_readers=[
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(
                        endpoint=settings.otel_endpoint or "http://localhost:4317"
                    )
                )
            ]
        )
    )
    
    # Create custom meters
    meter = metrics.get_meter("agenticfleet")
    
    # Define metrics
    agent_invocation_counter = meter.create_counter(
        "agent.invocations",
        description="Number of agent invocations"
    )
    
    token_usage_counter = meter.create_counter(
        "llm.tokens",
        description="LLM token usage"
    )
    
    workflow_duration_histogram = meter.create_histogram(
        "workflow.duration",
        description="Workflow execution duration in seconds"
    )
    
    return {
        "agent_invocations": agent_invocation_counter,
        "token_usage": token_usage_counter,
        "workflow_duration": workflow_duration_histogram,
    }


# Instrument agents
from agent_framework import ChatAgent

class InstrumentedChatAgent(ChatAgent):
    """ChatAgent with automatic instrumentation."""
    
    async def run(self, input: str):
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span(
            f"agent.run.{self.name}",
            attributes={
                "agent.name": self.name,
                "agent.model": self.model_id,
                "input.length": len(input),
            }
        ) as span:
            start_time = time.time()
            
            try:
                result = await super().run(input)
                
                # Record metrics
                span.set_attribute("output.length", len(result.content))
                span.set_attribute("tokens.used", result.usage.total_tokens)
                span.set_attribute("cost.usd", calculate_cost(result.usage))
                
                return result
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
                
            finally:
                duration = time.time() - start_time
                span.set_attribute("duration.seconds", duration)
```

## Benefits

### Performance
- ✅ **Identify Bottlenecks**: See which agents/tools are slow
- ✅ **Optimize Costs**: Track token usage per agent
- ✅ **Resource Planning**: Understand usage patterns
- ✅ **SLA Monitoring**: Track response times

### Debugging
- ✅ **Distributed Tracing**: Follow requests across agents
- ✅ **Error Root Cause**: See exactly where failures occur
- ✅ **Context Propagation**: Maintain context across services
- ✅ **Visual Traces**: UI for trace inspection

### Operations
- ✅ **Production Monitoring**: Real-time dashboards
- ✅ **Alerting**: Set up alerts on metrics
- ✅ **Capacity Planning**: Historical data analysis
- ✅ **Compliance**: Audit logs and traces

## Key Metrics to Track

### Agent Metrics
- Invocation count per agent
- Success/failure rate
- Average response time
- Token usage per agent
- Cost per agent

### Workflow Metrics
- Workflow completion rate
- End-to-end duration
- Number of agent handoffs
- Retry/failure count
- User satisfaction score

### LLM Metrics
- Token usage (prompt + completion)
- API call latency
- Cost per request
- Model version used
- Rate limit hits

### System Metrics
- Memory usage
- CPU utilization
- Error rate
- Throughput (requests/sec)

## Implementation Steps

### Phase 1: Basic Tracing (Week 1)
- [ ] Install OpenTelemetry packages
- [ ] Set up OTLP exporters
- [ ] Enable framework tracing
- [ ] Add environment configuration
- [ ] Test with local collector

### Phase 2: Custom Instrumentation (Week 1)
- [ ] Instrument agent invocations
- [ ] Add workflow spans
- [ ] Track tool calls
- [ ] Add custom metrics
- [ ] Test metric collection

### Phase 3: Integration (Week 2)
- [ ] Deploy OTEL collector
- [ ] Connect to backend (Jaeger/Grafana/etc)
- [ ] Create dashboards
- [ ] Set up alerting
- [ ] Document usage

## Configuration

```yaml
# config/observability.yaml
observability:
  enabled: true
  
  # OpenTelemetry Configuration
  otel:
    endpoint: "http://localhost:4317"
    insecure: true
    
    # Sampling
    sampling_rate: 1.0  # 1.0 = 100%, 0.1 = 10%
    
    # Exporters
    exporters:
      - type: otlp
        endpoint: "http://localhost:4317"
      - type: console  # For development
        enabled: false
  
  # Metrics
  metrics:
    enabled: true
    export_interval_seconds: 60
    custom_metrics:
      - agent_invocations
      - token_usage
      - workflow_duration
      - error_count
  
  # Tracing
  tracing:
    enabled: true
    sample_rate: 1.0
    max_attributes: 128
    max_events: 128
```

```bash
# .env additions
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=agenticfleet
OTEL_SERVICE_VERSION=0.6.0
```

## Backend Options

### Option 1: Jaeger (Local Development)
```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Access UI: http://localhost:16686
```

### Option 2: Grafana Stack (Production)
- Grafana for dashboards
- Tempo for traces
- Loki for logs
- Prometheus for metrics

### Option 3: Azure Monitor
```python
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

enable_tracing(
    service_name="agenticfleet",
    exporter=AzureMonitorTraceExporter(
        connection_string=settings.azure_monitor_connection_string
    )
)
```

## Example Dashboards

### Agent Performance Dashboard
- Agent invocation count (last 24h)
- Average response time per agent
- Token usage breakdown
- Cost per agent
- Error rate by agent

### Workflow Dashboard
- Active workflows
- Completion rate
- Average duration
- Bottleneck identification
- Most common paths

### Cost Dashboard
- Total LLM cost
- Cost per workflow
- Cost trends
- Token usage trends
- Cost by model

## Testing Requirements

### Unit Tests
```python
def test_tracing_enabled():
    """Test tracing is configured correctly."""
    setup_observability()
    tracer = trace.get_tracer("test")
    assert tracer is not None

def test_metrics_recorded():
    """Test metrics are recorded."""
    metrics = setup_observability()
    metrics["agent_invocations"].add(1, {"agent": "test"})
    # Verify metric was recorded
```

### Integration Tests
- Test trace propagation across agents
- Test metrics export to collector
- Test span creation and attributes
- Test error recording

## Estimated Effort
🔨 **Low** (3-5 days)

The framework provides built-in OpenTelemetry support, so implementation is straightforward.

## Dependencies
- opentelemetry-api
- opentelemetry-sdk
- opentelemetry-exporter-otlp
- agent-framework observability module

## Related Resources
- [Agent Framework Observability](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started/observability)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)

## Success Criteria
- ✅ Traces appear in visualization tool (Jaeger/Grafana)
- ✅ Can follow request across multiple agents
- ✅ Token usage is tracked accurately
- ✅ Custom metrics are exported
- ✅ Error traces include full context
- ✅ Dashboards show key metrics
- ✅ Performance overhead < 5%

---
Status: Ready for Implementation
Priority: Medium (Operational Value)
Related: #OPT-01, #OPT-04
