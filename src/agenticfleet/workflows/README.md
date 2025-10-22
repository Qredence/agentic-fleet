# Workflow as Agent Pattern

This module implements a reflection and retry pattern where a Worker generates responses and a Reviewer evaluates them. If not approved, the Worker regenerates based on feedback until the Reviewer approves.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow as Agent                        │
│                                                             │
│  ┌─────────┐         ┌──────────┐         ┌──────────┐   │
│  │  User   │────────▶│  Worker  │────────▶│ Reviewer │   │
│  │  Query  │         │          │         │          │   │
│  └─────────┘         └──────────┘         └──────────┘   │
│                            ▲                     │         │
│                            │   Not Approved      │         │
│                            │   (with feedback)   │         │
│                            └─────────────────────┘         │
│                                                             │
│                      Approved ──────────▶ External         │
│                                          Consumer          │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### Worker Executor

- Generates initial responses based on user queries
- Incorporates feedback from Reviewer to improve responses
- Maintains state for pending requests during retry cycle
- Emits only approved responses to external consumers

### Reviewer Executor

- Evaluates responses against quality criteria:
  - **Relevance**: Response addresses the query
  - **Accuracy**: Information is correct
  - **Clarity**: Response is easy to understand
  - **Completeness**: Response covers all aspects
- Provides structured feedback for improvements
- Only approves when all criteria are satisfied

## Usage

### Basic Usage

```python
from agenticfleet.workflows import run_workflow_agent

# Simple one-liner for quick tasks
await run_workflow_agent("Explain quantum computing in simple terms.")
```

### Custom Models

```python
from agenticfleet.workflows import run_workflow_agent

# Use specific models for Worker and Reviewer
await run_workflow_agent(
    query="Write a Python function to sort a list",
    worker_model="gpt-4.1-nano",
    reviewer_model="gpt-4.1",
)
```

### Direct Agent Control

```python
from agenticfleet.workflows import create_workflow_agent

# Create agent for more control
agent = create_workflow_agent(
    worker_model="gpt-4.1-nano",
    reviewer_model="gpt-4.1",
)

# Use streaming for real-time updates
async for event in agent.run_stream("Your query here"):
    print(f"Event: {event}")
```

### Custom Reviewer Criteria

```python
from agenticfleet.workflows.workflow_as_agent import (
    Reviewer,
    Worker,
    ReviewRequest,
    ReviewResponse,
)
from agent_framework import WorkflowBuilder, ChatMessage, Role
from agent_framework.openai import OpenAIChatClient
from pydantic import BaseModel

class StrictCodeReviewer(Reviewer):
    """Custom reviewer with strict code quality checks."""

    @handler
    async def review(self, request: ReviewRequest, ctx: WorkflowContext[ReviewResponse]) -> None:
        class _Response(BaseModel):
            feedback: str
            approved: bool

        messages = [
            ChatMessage(
                role=Role.SYSTEM,
                text=(
                    "You are a strict code reviewer. Approve only if:\n"
                    "- Code is syntactically correct\n"
                    "- Includes error handling\n"
                    "- Has proper type hints\n"
                    "- Includes docstrings\n"
                    "- Follows best practices"
                ),
            )
        ]
        messages.extend(request.user_messages)
        messages.extend(request.agent_messages)
        messages.append(ChatMessage(role=Role.USER, text="Please review the code."))

        response = await self._chat_client.get_response(
            messages=messages, response_format=_Response
        )
        parsed = _Response.model_validate_json(response.messages[-1].text)

        await ctx.send_message(
            ReviewResponse(
                request_id=request.request_id,
                feedback=parsed.feedback,
                approved=parsed.approved
            )
        )

# Use custom reviewer
worker_client = OpenAIChatClient(model_id="gpt-4.1-nano")
reviewer_client = OpenAIChatClient(model_id="gpt-4.1")
reviewer = StrictCodeReviewer(id="strict_reviewer", chat_client=reviewer_client)
worker = Worker(id="worker", chat_client=worker_client)

agent = (
    WorkflowBuilder()
    .add_edge(worker, reviewer)
    .add_edge(reviewer, worker)
    .set_start_executor(worker)
    .build()
    .as_agent()
)

async for event in agent.run_stream("Write a function to read a JSON file"):
    print(event)
```

## Files

- `src/agenticfleet/workflows/workflow_as_agent.py` - Core implementation
- `examples/workflow_as_agent_example.py` - Usage examples
- `notebooks/agent_as_workflow.ipynb` - Interactive tutorial

## Running Examples

```bash
# Run the comprehensive examples
uv run python examples/workflow_as_agent_example.py

# Or explore interactively in Jupyter
jupyter notebook notebooks/agent_as_workflow.ipynb
```

## Integration with AgenticFleet

This workflow pattern can be integrated into larger AgenticFleet orchestrations:

```python
from agenticfleet import create_default_fleet
from agenticfleet.workflows import create_workflow_agent

# Create the main fleet
fleet = create_default_fleet()

# Create a quality-controlled workflow agent
qa_agent = create_workflow_agent(
    worker_model="gpt-4.1-nano",
    reviewer_model="gpt-4.1",
)

# Use in coordination with other agents
# (Integration patterns depend on your specific use case)
```

## Benefits

1. **Quality Assurance**: Automated review cycle ensures high-quality outputs
2. **Iterative Improvement**: Failed responses are regenerated with specific feedback
3. **Type Safety**: Structured communication using Pydantic models
4. **Composability**: Can be wrapped as an agent for use in larger workflows
5. **Observability**: Progress tracking through print statements (can be replaced with proper logging)

## Limitations

- No retry limit by default (can lead to infinite loops with incompatible criteria)
- Print-based observability (should be replaced with proper logging for production)
- Single review dimension (extend Reviewer for multi-aspect reviews)

## Future Enhancements

- Add retry limits to prevent infinite loops
- Implement metrics tracking (review iterations, approval rate)
- Support multiple reviewers for different aspects (code, security, performance)
- Add human-in-the-loop approval for sensitive operations
- Integrate with AgenticFleet's checkpoint system for state persistence

## Related Documentation

- [Magentic Fleet Architecture](../docs/architecture/magentic-fleet.md)
- [Agent Development Guide](../../docs/project/AGENTS.md)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
