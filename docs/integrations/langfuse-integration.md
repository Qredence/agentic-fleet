# Langfuse Integration Guide

This document describes the Langfuse tracing integration for AgenticFleet, which provides comprehensive observability for DSPy and Microsoft Agent Framework calls.

## Overview

The integration automatically traces:

- **DSPy calls**: All DSPy module invocations (reasoner, analyzer, router, quality assessor, etc.)
- **OpenAI SDK calls**: All OpenAI API calls made through the Agent Framework
- **Microsoft Agent Framework**: Traced indirectly through wrapped OpenAI clients

## Setup

### 1. Install Dependencies

```bash
uv pip install langfuse openinference-instrumentation-dspy
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Langfuse Tracing
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com  # EU region
# LANGFUSE_BASE_URL=https://us.cloud.langfuse.com  # US region
```

Get your keys from: https://cloud.langfuse.com → Project Settings

### 3. Verify Integration

When you start your application, you should see these log messages:

```
Langfuse client initialized successfully
DSPy instrumentation enabled for Langfuse tracing with framework detection
Created Langfuse trace <trace_id> with framework metadata
```

## How It Works

### Trace Structure

Traces are automatically organized in a hierarchical structure:

```
Workflow Trace (AgenticFleet)
├── DSPy.TaskAnalysis (DSPy framework)
├── DSPy.TaskRouting (DSPy framework)
├── AgentFramework.AgentExecution (Microsoft Agent Framework)
│   └── OpenAI Generation (OpenAI SDK)
└── DSPy.QualityAssessment (DSPy framework)
```

### Framework Detection

- **DSPy calls** are automatically tagged with `framework: DSPy` and `tags: ["dspy", "reasoning"]`
- **Agent Framework calls** are tagged with `framework: Microsoft Agent Framework` and `tags: ["agent-framework", "microsoft"]`
- **Workflow traces** are tagged with `framework: AgenticFleet` and `tags: ["workflow", "agentic-fleet"]`

### Trace Grouping

Traces are automatically grouped by:

- **Session ID**: Extracted from conversation threads (if available)
- **Workflow ID**: Unique identifier for each workflow execution
- **User ID**: Can be set via context (see below)

## Advanced Features

### Adding Custom Metadata

You can add custom metadata to traces using the Langfuse utilities:

```python
from agentic_fleet.utils.infra.langfuse import set_langfuse_context

# Set context for current request
set_langfuse_context(
    user_id="user_123",
    session_id="session_abc",
    metadata={"experiment": "variant_a", "env": "production"},
    tags=["production", "experiment"],
)
```

### Evaluation: LLM as Judge

Use LLM as a judge to automatically evaluate trace quality:

```python
from agentic_fleet.evaluation.langfuse_eval import evaluate_with_llm_judge

# Evaluate a trace using LLM as judge
result = evaluate_with_llm_judge(
    trace_id="your-trace-id",
    criteria="Is the response accurate, complete, and helpful?",
    model="gpt-4o-mini",
    score_name="quality_score",
)

print(f"Score: {result['score']}")
print(f"Explanation: {result['explanation']}")
```

### Adding Custom Scores

Add custom scores to traces for evaluation:

```python
from agentic_fleet.evaluation.langfuse_eval import add_custom_score

# Add a score to a trace
add_custom_score(
    trace_id="your-trace-id",
    name="user_satisfaction",
    value=0.9,  # 0.0 to 1.0
    comment="User rated response as helpful",
    metadata={"source": "user_feedback"},
)
```

### Creating Dashboards

In Langfuse Cloud, you can:

1. **Filter by Framework**: Use tags to filter traces:
   - `dspy` - DSPy calls only
   - `agent-framework` - Agent Framework calls only
   - `workflow` - Complete workflow traces

2. **Filter by Metadata**: Use metadata fields:
   - `framework: DSPy` - DSPy framework calls
   - `framework: Microsoft Agent Framework` - Agent Framework calls
   - `workflow_mode: standard` - Filter by execution mode

3. **Group by Session**: View all traces in a conversation session

4. **Cost Analysis**: Track token usage and costs per framework

### Trace URLs

Get trace URLs for sharing:

```python
from langfuse import get_client

langfuse = get_client()
trace_id = langfuse.get_current_trace_id()
trace_url = langfuse.get_trace_url(trace_id=trace_id)
print(f"View trace: {trace_url}")
```

## Troubleshooting

### Traces Not Appearing

1. **Check Credentials**: Verify `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set correctly
2. **Check Region**: Ensure `LANGFUSE_BASE_URL` matches your region (EU/US)
3. **Check Logs**: Look for "Langfuse client initialized successfully" message
4. **Wait**: Traces may take a few seconds to appear in the dashboard

### DSPy Calls Not Detected

- Ensure `openinference-instrumentation-dspy` is installed
- Check logs for "DSPy instrumentation enabled" message
- Verify DSPy is configured before Langfuse initialization

### Agent Framework Calls Not Detected

- Ensure OpenAI clients are created via `create_openai_client_with_store()`
- Check logs for "OpenAI client wrapped with Langfuse tracing" message
- Verify Langfuse credentials are available when clients are created

### Framework Not Properly Tagged

- Check trace metadata in Langfuse UI - should show `framework: DSPy` or `framework: Microsoft Agent Framework`
- Verify you're using the latest version of the integration
- Check that `propagate_attributes` is being called with framework metadata

## Best Practices

1. **Session IDs**: Always set session IDs for multi-turn conversations to group related traces
2. **User IDs**: Set user IDs for user-specific analytics and filtering
3. **Tags**: Use tags to categorize traces (e.g., `production`, `experiment`, `debug`)
4. **Metadata**: Add relevant metadata (workflow mode, agent names, etc.) for better filtering
5. **Evaluations**: Use LLM as judge or custom scores to track quality over time

## API Reference

### Langfuse Utilities

Located in `src/agentic_fleet/utils/infra/langfuse.py`:

- `set_langfuse_context()` - Set trace context (user_id, session_id, metadata, tags)
- `get_langfuse_context()` - Get current trace context
- `create_workflow_trace()` - Create a workflow trace (deprecated, use supervisor integration)
- `create_dspy_span()` - Create a DSPy span (deprecated, auto-instrumented)
- `create_agent_framework_span()` - Create an Agent Framework span (deprecated, auto-instrumented)

### Evaluation Utilities

Located in `src/agentic_fleet/evaluation/langfuse_eval.py`:

- `evaluate_with_llm_judge()` - Evaluate trace using LLM as judge
- `add_custom_score()` - Add custom score to trace

## Examples

### Example 1: Basic Usage

No code changes needed! Just set environment variables and traces are automatically created.

### Example 2: Adding User Context

```python
from agentic_fleet.utils.infra.langfuse import set_langfuse_context

# In your API route handler
set_langfuse_context(
    user_id=request.user.id,
    session_id=conversation_id,
    tags=["api", "production"],
)
```

### Example 3: Evaluating Traces

```python
from agentic_fleet.evaluation.langfuse_eval import evaluate_with_llm_judge

# After workflow completes
trace_id = workflow_id  # Use your workflow_id
evaluation = evaluate_with_llm_judge(
    trace_id=trace_id,
    criteria="Is the response accurate and complete?",
    model="gpt-4o-mini",
)
```

## Integration Points

The integration hooks into these key points:

1. **DSPy Initialization** (`dspy_modules/lifecycle/manager.py`):
   - Instruments DSPy before configuration
   - Adds framework metadata to all DSPy calls

2. **OpenAI Client Creation** (`workflows/helpers/execution.py`):
   - Wraps OpenAI clients with Langfuse tracing
   - Adds framework metadata to Agent Framework calls

3. **Workflow Execution** (`workflows/supervisor.py`):
   - Creates top-level workflow traces
   - Sets trace context for nested spans
   - Updates traces with final results

## Next Steps

1. **Explore Traces**: Go to Langfuse Cloud and explore your traces
2. **Set Up Dashboards**: Create custom dashboards for your metrics
3. **Add Evaluations**: Set up LLM-as-judge evaluations for quality tracking
4. **Monitor Costs**: Track token usage and costs per framework
5. **Optimize**: Use trace data to identify bottlenecks and optimize workflows
