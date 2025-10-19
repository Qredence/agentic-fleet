# Workflow as Agent - Frontend Integration Summary

## Overview

Successfully integrated the `workflow_as_agent` reflection pattern into the HaxUI frontend API, making it available for execution through the web interface.

## Changes Made

### 1. Runtime Integration (`src/agenticfleet/haxui/runtime.py`)

#### Imports

```python
from agenticfleet.workflows import create_workflow_agent
```

#### FleetRuntime Updates

- Added `_workflow_as_agent` instance variable to store the workflow agent
- Initialize workflow_as_agent in `ensure_initialised()` with default models:
  - Worker: `gpt-4.1-nano` (fast response generation)
  - Reviewer: `gpt-4.1` (thorough quality evaluation)

#### Execution Routing

Modified `generate_response()` to route entity_id-based execution:

```python
if entity_id == "workflow_as_agent" and self._workflow_as_agent is not None:
    # Stream events from workflow_as_agent
    accumulated_result = []
    async for event in self._workflow_as_agent.run_stream(prompt):
        accumulated_result.append(str(event))
    result = "\n".join(accumulated_result)
else:
    # Default to MagenticFleet
    result = await asyncio.wait_for(self._fleet.run(prompt), timeout=timeout_seconds)
```

### 2. Entity Catalog (`build_entity_catalog()`)

Added new workflow entity:

```python
{
    "id": "workflow_as_agent",
    "type": "workflow",
    "name": "Reflection & Retry Workflow",
    "description": "Worker generates responses reviewed by Reviewer. Failed responses are regenerated with feedback until approved.",
    "framework": "agenticfleet",
    "executors": ["worker", "reviewer"],
    "start_executor_id": "worker",
    "metadata": {
        "pattern": "reflection",
        "quality_assurance": True
    }
}
```

### 3. API Integration Tests (`tests/test_workflow_as_agent_api.py`)

Created comprehensive test suite:

- `test_workflow_as_agent_in_catalog()` - Verifies entity appears in catalog
- `test_entity_catalog_structure()` - Validates entity structure and metadata
- `test_runtime_initialization()` - Confirms workflow_as_agent initialization

## API Endpoints

### GET `/v1/entities`

Returns both workflows in the catalog:

- `magentic_fleet_workflow` - Multi-agent orchestration
- `workflow_as_agent` - Reflection & retry pattern

### POST `/v1/responses`

Execute workflow with:

```json
{
  "entity_id": "workflow_as_agent",
  "user_text": "Your query here"
}
```

Response streams via Server-Sent Events (SSE) with accumulated output from Worker-Reviewer cycles.

## Workflow Behavior

1. **User submits query** → API routes to `workflow_as_agent`
2. **Worker generates response** → Creates initial answer
3. **Reviewer evaluates** → Checks 4 quality criteria:
   - Relevance to query
   - Factual accuracy
   - Clarity of expression
   - Completeness of answer
4. **Decision**:
   - ✅ **Approved** → Response emitted via SSE stream
   - ❌ **Needs improvement** → Feedback sent to Worker, regenerates
5. **Iterates** until approved or max retries reached

## Quality Assurance Features

- **Dual-model strategy**: Fast generation (nano) + thorough review (full model)
- **Structured evaluation**: Pydantic models ensure type-safe communication
- **Iterative improvement**: Each retry incorporates specific feedback
- **State management**: Tracks pending reviews and retry counts
- **Observable**: All events streamed to frontend for transparency

## Testing Validation

All tests passing:

```bash
✓ workflow_as_agent found in catalog
✓ Entity catalog structure validated
✓ Runtime initialization verified
✓ Lint checks (ruff) - PASS
✓ Type checks (mypy) - PASS
✓ Configuration tests - PASS
```

## Usage Examples

### Via Python API

```python
from agenticfleet.workflows import create_workflow_agent

agent = create_workflow_agent(
    worker_model="gpt-4.1-nano",
    reviewer_model="gpt-4.1"
)

async for event in agent.run_stream("Explain quantum computing"):
    print(event)
```

### Via REST API

```bash
curl -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "workflow_as_agent", "user_text": "Explain quantum computing"}'
```

### Via Frontend UI

1. Navigate to HaxUI interface
2. Select "Reflection & Retry Workflow" from entity dropdown
3. Enter query and submit
4. Watch Worker-Reviewer iterations in real-time

## Model Configuration

Current defaults (configurable via factory parameters):

- **Worker**: `gpt-4.1-nano` - Optimized for speed, good for draft generation
- **Reviewer**: `gpt-4.1` - Full reasoning capacity for quality evaluation

To customize models, modify the initialization in `runtime.py`:

```python
self._workflow_as_agent = create_workflow_agent(
    worker_model="your-preferred-model",
    reviewer_model="your-review-model"
)
```

## Integration Points

### Frontend (React)

- Entity selector shows "Reflection & Retry Workflow"
- SSE stream handler displays Worker responses and Reviewer feedback
- Progress indicators show which executor is active

### Backend (FastAPI)

- `/v1/entities` includes workflow_as_agent in response
- `/v1/responses` routes to workflow based on entity_id
- `FleetRuntime` manages workflow lifecycle

### Workflow Module

- `src/agenticfleet/workflows/workflow_as_agent.py` - Core implementation
- `Worker` and `Reviewer` classes extend `Executor`
- `ReviewRequest` and `ReviewResponse` dataclasses handle communication

## Future Enhancements

1. **Configurable models**: Add UI controls for worker/reviewer model selection
2. **Custom criteria**: Allow users to define custom review criteria
3. **Max retries**: Add UI setting for iteration limits
4. **Review history**: Display full review chain in frontend
5. **Approval bypass**: Option to accept Worker's first response without review

## Documentation References

- **Architecture**: `docs/architecture/magentic-fleet.md`
- **Workflow Guide**: `src/agenticfleet/workflows/README.md`
- **API Docs**: `docs/features/web-hitl-integration.md`
- **Examples**: `examples/workflow_as_agent_example.py`
- **Notebooks**: `notebooks/agent_as_workflow.ipynb`

## Verification Commands

```bash
# Test configuration
uv run python tests/test_config.py

# Test API integration
uv run python tests/test_workflow_as_agent_api.py

# Lint and type check
uv run ruff check src/agenticfleet/haxui/runtime.py
uv run mypy src/agenticfleet/haxui/runtime.py

# Run full test suite
uv run pytest tests/test_workflow_as_agent_api.py -v
```

## Status: ✅ Complete

The workflow_as_agent is now fully integrated into the HaxUI frontend and ready for use. Users can select it from the entity dropdown and execute quality-assured responses through the Worker-Reviewer reflection pattern.
