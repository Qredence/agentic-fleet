# Workflow as Agent - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React + TypeScript)                │
│                                                                       │
│  ┌──────────────┐         ┌────────────────────────────────┐        │
│  │ Entity       │         │  Streaming Response Display    │        │
│  │ Selector     │────────▶│  - Worker output               │        │
│  │              │         │  - Reviewer feedback           │        │
│  │ • Magentic   │         │  - Iteration count             │        │
│  │   Fleet      │         └────────────────────────────────┘        │
│  │ • Workflow   │                                                    │
│  │   as Agent ✓ │                                                    │
│  └──────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP / SSE
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      HaxUI API (FastAPI Backend)                     │
│                                                                       │
│  GET /v1/entities                                                    │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │ build_entity_catalog()                                   │       │
│  │  - agents: ["magentic_fleet"]                           │       │
│  │  - workflows: ["magentic_fleet_workflow",              │       │
│  │                "workflow_as_agent" ✓]                  │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                       │
│  POST /v1/responses                                                  │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │ FleetRuntime.generate_response(entity_id, prompt)       │       │
│  │                                                          │       │
│  │  if entity_id == "workflow_as_agent":                  │       │
│  │    ➜ self._workflow_as_agent.run_stream(prompt)       │       │
│  │  else:                                                 │       │
│  │    ➜ self._fleet.run(prompt)                          │       │
│  └──────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                       ┌────────────┴────────────┐
                       │                         │
                       ▼                         ▼
        ┌───────────────────────┐   ┌──────────────────────┐
        │  MagenticFleet        │   │ Workflow as Agent    │
        │  (Multi-Agent)        │   │ (Reflection Pattern) │
        └───────────────────────┘   └──────────────────────┘
                                              │
                                              │
                        ┌─────────────────────┴──────────────────────┐
                        │                                            │
                        ▼                                            ▼
          ┌──────────────────────┐                    ┌──────────────────────┐
          │      Worker          │◀──────feedback─────│      Reviewer        │
          │  (gpt-4.1-nano)     │                    │    (gpt-4.1)         │
          │                      │                    │                      │
          │ • Generate response  │                    │ • Evaluate quality   │
          │ • Accept feedback    │                    │ • Provide feedback   │
          │ • Retry on rejection │───review request──▶│ • Approve/Reject     │
          └──────────────────────┘                    └──────────────────────┘
                     │
                     │ approved response
                     ▼
          ┌──────────────────────┐
          │  AgentRunUpdateEvent │
          │  (emitted to stream) │
          └──────────────────────┘
```

## Data Flow

### 1. Entity Discovery

```
Frontend → GET /v1/entities → build_entity_catalog() → Returns workflows list
```

### 2. Workflow Execution

```
User Input → POST /v1/responses → FleetRuntime.generate_response()
   │
   ├─ entity_id: "workflow_as_agent"
   │     │
   │     └─▶ create_workflow_agent() instance
   │           │
   │           └─▶ run_stream(prompt)
   │                 │
   │                 ├─▶ Worker.handle_user_messages()
   │                 │     └─▶ generate initial response
   │                 │           └─▶ send ReviewRequest to Reviewer
   │                 │
   │                 ├─▶ Reviewer.review()
   │                 │     └─▶ evaluate against 4 criteria
   │                 │           ├─▶ APPROVED → emit response
   │                 │           └─▶ NEEDS_IMPROVEMENT → feedback to Worker
   │                 │
   │                 └─▶ Worker.handle_review_response()
   │                       ├─▶ if approved: emit AgentRunUpdateEvent
   │                       └─▶ if rejected: regenerate with feedback
   │
   └─ entity_id: "magentic_fleet_workflow"
         └─▶ MagenticFleet.run(prompt)
```

### 3. Response Streaming

```
Workflow Events → SSE Stream → Frontend Real-time Display
   │
   ├─ Worker output: "Here's my response..."
   ├─ Reviewer feedback: "Needs more detail on X..."
   ├─ Worker retry: "Enhanced response with..."
   └─ Final approval: "✓ Response approved"
```

## Quality Criteria

The Reviewer evaluates responses on:

1. **Relevance** (0-5): Does it address the query?
2. **Accuracy** (0-5): Is information factually correct?
3. **Clarity** (0-5): Is it well-structured and understandable?
4. **Completeness** (0-5): Does it fully answer the question?

**Threshold**: Average score ≥ 4.0 to approve

## Key Components

### Runtime (`src/agenticfleet/haxui/runtime.py`)

- `FleetRuntime.__init__()` - Initialize workflow_as_agent instance
- `FleetRuntime.generate_response()` - Route execution based on entity_id
- `build_entity_catalog()` - Register workflow in API catalog

### Workflow (`src/agenticfleet/workflows/workflow_as_agent.py`)

- `Worker` - Generates and refines responses
- `Reviewer` - Evaluates quality against criteria
- `ReviewRequest` / `ReviewResponse` - Communication protocol
- `create_workflow_agent()` - Factory function for initialization

### API (`src/agenticfleet/haxui/api.py`)

- `/v1/entities` - List available workflows
- `/v1/responses` - Execute selected workflow
- SSE streaming for real-time feedback

## Configuration

### Default Models

```python
create_workflow_agent(
    worker_model="gpt-4.1-nano",    # Fast generation
    reviewer_model="gpt-4.1"         # Thorough evaluation
)
```

### Customization Points

- Worker/Reviewer models (configurable in runtime.py)
- Quality criteria thresholds (in Reviewer.review())
- Max retry attempts (in Worker state management)
- Evaluation rubric (ReviewResponse fields)

## Benefits

✅ **Quality Assurance**: Every response is reviewed before delivery
✅ **Iterative Improvement**: Failed responses are enhanced with specific feedback
✅ **Observable**: All interactions visible in real-time stream
✅ **Dual-Speed**: Fast generation + thorough review for optimal cost/quality
✅ **Type-Safe**: Pydantic models ensure reliable communication
✅ **Extensible**: Easy to add custom review criteria or workflows
