# Langfuse Quick Reference

Quick reference guide for using Langfuse features with AgenticFleet.

## Framework Detection in Langfuse

### Filtering Traces by Framework

In Langfuse Cloud UI:

1. **DSPy Traces**: Filter by tag `dspy` or metadata `framework: DSPy`
2. **Agent Framework Traces**: Filter by tag `agent-framework` or metadata `framework: Microsoft Agent Framework`
3. **Complete Workflows**: Filter by tag `workflow` or metadata `framework: AgenticFleet`

### Trace Structure

```
Trace: Workflow: standard
├── Metadata: framework=AgenticFleet, workflow_mode=standard
├── Span: DSPy.TaskAnalysis
│   └── Metadata: framework=DSPy, dspy_module=analyzer
├── Span: DSPy.TaskRouting
│   └── Metadata: framework=DSPy, dspy_module=router
└── Span: AgentFramework.AgentExecution
    └── Generation: OpenAI Chat Completion
        └── Metadata: framework=Microsoft Agent Framework
```

## Evaluations

### LLM as Judge

```python
from agentic_fleet.evaluation.langfuse_eval import evaluate_with_llm_judge

# Evaluate a trace
result = evaluate_with_llm_judge(
    trace_id="your-trace-id",
    criteria="Is the response accurate, complete, and helpful?",
    model="gpt-4o-mini",
    score_name="quality_score",
)
```

### Custom Scores

```python
from agentic_fleet.evaluation.langfuse_eval import add_custom_score

# Add numeric score (0.0 to 1.0)
add_custom_score(
    trace_id="your-trace-id",
    name="accuracy",
    value=0.95,
    comment="Verified against ground truth",
)

# Add categorical score
add_custom_score(
    trace_id="your-trace-id",
    name="sentiment",
    value="positive",
    comment="User feedback",
)
```

### Scoring from Workflow

```python
from agentic_fleet.evaluation.langfuse_eval import add_custom_score
from langfuse import get_client

# In your workflow completion handler
langfuse = get_client()
trace_id = langfuse.get_current_trace_id()

if trace_id:
    add_custom_score(
        trace_id=trace_id,
        name="workflow_quality",
        value=final_msg.quality.score / 10.0,  # Convert 0-10 to 0-1
        comment=final_msg.quality.improvements,
    )
```

## Dashboards

### Creating Custom Dashboards

1. Go to Langfuse Cloud → Dashboards
2. Click "Create Dashboard"
3. Add metrics:
   - **Cost by Framework**: Filter by `framework` metadata
   - **Latency by Phase**: Filter by `phase` metadata
   - **Error Rate**: Filter by status
   - **Token Usage**: Group by framework

### Useful Filters

- `framework: DSPy` - DSPy calls only
- `framework: Microsoft Agent Framework` - Agent Framework calls
- `tags: workflow` - Complete workflow traces
- `workflow_mode: standard` - Filter by execution mode
- `session_id: <id>` - All traces in a session

## Grouping Traces

### By Session

Traces are automatically grouped by `session_id` when available. Set it via:

```python
from agentic_fleet.utils.infra.langfuse import set_langfuse_context

set_langfuse_context(session_id="conversation-123")
```

### By User

```python
set_langfuse_context(user_id="user-456")
```

### By Experiment

```python
set_langfuse_context(
    tags=["experiment", "variant-a"],
    metadata={"experiment_id": "exp-001"},
)
```

## Trace URLs

### Get Trace URL

```python
from langfuse import get_client

langfuse = get_client()
trace_id = langfuse.get_current_trace_id()
url = langfuse.get_trace_url(trace_id=trace_id)
```

### Share Trace

```python
# Make trace public for sharing
langfuse.update_current_trace(public=True)
```

## Metadata Examples

### Workflow Metadata

Automatically added:

- `workflow_id`: Unique workflow identifier
- `workflow_mode`: Execution mode (standard, handoff, group_chat)
- `framework`: AgenticFleet
- `reasoning_effort`: Reasoning effort level
- `phase_timings`: Timing for each phase
- `phase_status`: Status of each phase

### DSPy Metadata

Automatically added:

- `framework`: DSPy
- `dspy_module`: Module name (analyzer, router, etc.)
- `dspy_signature`: Signature name

### Agent Framework Metadata

Automatically added:

- `framework`: Microsoft Agent Framework
- `agent_name`: Name of the agent
- `phase`: Workflow phase

## Common Queries

### Find Expensive Traces

Filter by: `cost > $0.10` or `total_tokens > 10000`

### Find Slow Traces

Filter by: `latency > 5s` or sort by latency descending

### Find Failed Traces

Filter by: `status: error` or `tags: error`

### Compare Frameworks

Create dashboard comparing:

- Average cost: DSPy vs Agent Framework
- Average latency: DSPy vs Agent Framework
- Token usage: DSPy vs Agent Framework

## Integration Checklist

- [ ] Langfuse credentials configured in `.env`
- [ ] Packages installed: `langfuse`, `openinference-instrumentation-dspy`
- [ ] Logs show "Langfuse client initialized successfully"
- [ ] Traces appear in Langfuse Cloud
- [ ] Framework tags visible in trace metadata
- [ ] DSPy calls show `framework: DSPy` metadata
- [ ] Agent Framework calls show `framework: Microsoft Agent Framework` metadata
- [ ] Traces are properly grouped by session_id
