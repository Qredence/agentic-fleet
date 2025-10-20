# Dynamic Magentic Workflow

The dynamic workflow scaffolding under `agenticfleet.workflows.dynamic` builds a Magentic orchestration that mirrors the progress-ledger routing in `agent_framework._workflows._magentic` (see `_run_inner_loop_locked`). It exposes composable factories for backbone modules and optional tool participants so you can customise the roster while relying on the manager's JSON ledger to decide which participant acts next.

## Package Layout

```
agenticfleet/workflows/dynamic/
├── factory.py                # `create_dynamic_workflow` entry point
├── modules/                  # Backbone participants
│   ├── planner.py            # `create_planner_participant`
│   ├── executor.py           # `create_executor_participant`
│   ├── verifier.py           # `create_verifier_participant`
│   ├── generator.py          # `create_generator_participant`
│   ├── backbone.py           # Aggregates backbone participants
│   └── participants.py       # `DynamicWorkflowParticipants`
├── tools/                    # Tool participants registered as peers
│   ├── google_search.py      # Hosted web search participant
│   ├── wikipedia_search.py   # Wikipedia-focused search
│   ├── python_coder.py       # Code interpreter participant
│   ├── base_generator.py     # Baseline writer
│   └── participants.py       # Aggregates tool participants
├── prompts/                  # Prompt text per participant type
│   ├── manager.py
│   ├── modules.py
│   └── tools.py
└── settings/                 # Helper utilities for clients + manager limits
    ├── clients.py
    └── manager.py
```

## Quick Start

```python
from agenticfleet.workflows.dynamic import (
    create_dynamic_workflow,
    create_default_dynamic_participants,
)
from agenticfleet.workflows.dynamic.tools import create_python_coder_participant

# Option 1: Use defaults (planner/executor/verifier/generator + tool agents)
workflow = create_dynamic_workflow()

# Option 2: Bring your own participants
custom_participants = create_default_dynamic_participants(
    include_tool_agents=False,
).as_dict()
custom_participants["python_coder"] = create_python_coder_participant()
workflow = create_dynamic_workflow(participants=custom_participants)

# Execute a task (mirrors Magentic's run API)
result = await workflow.run("Build a Python web scraper")
```

### CLI Shortcut

Install the package (or run inside the repo) and invoke:

```
uv run dynamic-fleet "Build a Python web scraper"
```

Use `--no-tools` to disable optional tool participants or `--manager-model` to override the
manager LLM.

Internally the workflow uses `StandardMagenticManager` to manage facts, plan, and progress ledgers. The manager produces the instruction and `next_speaker`, and the orchestrator routes requests to the matching participant executor (`agent_<name>`). Tool agents behave as first-class participants, so the ledger can select them whenever progress requires.

## Customising Participants

Each module/tool has a factory that accepts overrides:

```python
from agenticfleet.workflows.dynamic.modules import create_planner_participant
from agenticfleet.workflows.dynamic.tools import create_google_search_participant

planner = create_planner_participant(model="gpt-4.1-mini")
web_search = create_google_search_participant(instructions="Use short bullet summaries.")
```

You can mix and match participants before passing them to `create_dynamic_workflow`. All factories return instances compatible with `agent_framework.AgentProtocol`.

## Manager Adjustments

Use `create_dynamic_workflow` kwargs to override manager settings:

```python
workflow = create_dynamic_workflow(
    manager_instructions="Coordinate agents with an emphasis on cost control.",
    manager_model="gpt-4o",
    progress_ledger_retry_count=3,
)
```

The helper `settings.manager.build_manager_kwargs` centralises round/stall/reset limits sourced from `workflow.yaml` (keys `max_rounds`, `max_stalls`, `max_resets`).

Set `defaults.tool_model` in `workflow.yaml` (defaults to `gpt-4.1-mini`) if you need to choose a
different model that supports hosted tools like web search or the code interpreter.

## Testing & Validation

- `tests/test_dynamic_workflow.py` exercises backbone-only setup. Extend this test or add new ones when registering additional participants.
- Use `workflow.run_stream` to observe Magentic callback events (planner instructions, agent outputs, final result).

## When to Use This Layer

- You need dynamic Magentic orchestration without the full CLI/fleet wrapper.
- You want to prototype new agents or prompts while relying on the built-in progress-ledger coordination.
- You plan to embed this workflow in another service but still leverage Magentic's adaptive routing (planner → tool → executor → verifier, etc.).

For deeper integration with the CLI or checkpoints, use `agenticfleet.fleet.magentic_fleet.MagenticFleet`, which builds on the same primitives but adds observability, approvals, and checkpoint wiring.
