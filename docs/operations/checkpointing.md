# Checkpointing & Persistent Memory

This guide explains how AgenticFleet keeps long-running workflows resilient
through checkpointing and how it pairs with the shared Mem0 memory layer.

## Why Checkpoints Matter

Magentic workflows may span multiple agent hand-offs. Checkpoints make it
possible to pause, resume, or recover from transient failures without losing
progress:

- **Resilience** – if the process or network dies mid-run, restart from the last
  saved round instead of the beginning.
- **Iteration** – experiment with prompt tweaks or agent settings while
  replaying from the previous checkpoint to compare outputs.
- **Auditing** – checkpoints provide a timeline of key orchestration states for
  observability and debugging.

## Configuration Overview

Checkpoint behaviour is controlled in `src/agenticfleet/config/workflow.yaml`:

```yaml
workflow:
  checkpointing:
    enabled: true
    storage_type: file         # or "memory"
    storage_path: ./checkpoints
    cleanup_after_days: 30
    auto_resume_on_failure: false
```

- **`storage_type: file`** persists JSON snapshots to disk (default).
- **`storage_type: memory`** stores checkpoints in memory for the process
  lifetime—handy during tests.
- **`cleanup_after_days`** prunes stale checkpoints automatically when the
  process starts.

The `Settings.create_checkpoint_storage()` helper translates this configuration
into the correct `CheckpointStorage` implementation and ensures the target
directory exists.

## CLI Usage

The REPL exposes a few commands that interact with checkpoints:

- `checkpoints` / `list-checkpoints` – enumerate available snapshots with round
  numbers and timestamps.
- `resume <checkpoint_id>` – continue the next task from a stored state. The
  next prompt you enter becomes the resumed user request.

Behind the scenes, `MagenticFleet.run()` forwards `resume_from_checkpoint` to
the Magentic workflow so the manager can reload the saved ledger and continue
planning from the last round.

## Relationship to Mem0

Checkpoints capture the conversational ledger and agent state _within a single
workflow run_. Mem0 complements this by providing cross-run memories that encode
facts about the user or prior work. Mem0 is backed by OpenAI models (no Azure
dependency) and stores history in a local database (`memories/history.db` by
default). Together they offer:

- **Short-term recall** – checkpoints rebuild the task ledger exactly as the
  planner saw it.
- **Long-term recall** – Mem0 supplies the `{memory}` blocks embedded in system
  prompts so agents remember preferences, facts, or previous outcomes.

Both layers are optional—disable checkpointing in `workflow.yaml` or point
Mem0 to a different store using the environment variables documented in
`docs/operations/mem0-integration.md`.

## Best Practices

1. **Keep storage tidy** – run `make clean` before committing to avoid shipping
   checkpoint artefacts. The repository `.gitignore` already excludes the
   default directory.
2. **Name checkpoints meaningfully** – when resuming via the CLI, note the
   generated identifier and why you stopped there (a quick note in your PR or
   tracker helps).
3. **Pair with runtime flags** – the new agent `runtime` blocks (`stream`,
   `store`, `checkpoint`) let you coordinate which agents should contribute to
   memory and when to persist state.

With checkpointing and Mem0 configured, AgenticFleet can survive restarts,
provide richer context to agents, and evolve into more robust multi-session
automation.
