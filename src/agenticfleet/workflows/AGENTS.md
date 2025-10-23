# AGENTS.md – Workflows Layer

> Agent-oriented guide to the `workflows/` module. Focus: how to use, extend, and safely modify workflow orchestrations (Magentic fleet variants, reflection workflows, experimental dynamic planners).

---

## 1. Purpose

The workflows layer encapsulates **higher-order orchestration patterns** that wrap or configure the underlying Magentic Fleet / ChatAgent graph. It allows exposing variants (e.g., reflection-based retry loops, dynamic adaptive planners) behind stable CLI / API interfaces.

---

## 2. Directory Snapshot

```
workflows/
├── __init__.py                 # Re-exports primary entrypoints
├── README.md                   # (Human / architectural notes, if present)
├── workflow_as_agent.py        # Reflection & reviewer-style workflow
├── _experimental_dynamic.py    # Adaptive dynamic workflow prototype
└── _experimental_dynamic/      # (Submodules / utilities for dynamic mode)
```

Naming conventions:

- Public (supported) modules: no leading underscore
- Experimental / unstable: prefix with `_experimental_`

---

## 3. Core Concepts

| Concept           | Description                                                                                                                     |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Fleet Wrapper     | A function/class that builds a specific configured `MagenticFleet` instance or similar orchestrator with altered loop semantics |
| Reflection Cycle  | Augments execution with evaluator steps (worker → reviewer → improved plan)                                                     |
| Dynamic Planning  | Runtime expansion / pruning of agent roles or tools based on task analysis                                                      |
| Workflow-as-Agent | Exposes an entire multi-agent workflow as a single logical agent interface                                                      |

---

## 4. `workflow_as_agent.py`

Pattern: Treat a multi-phase reflection loop as if it were a single agent. Typical phases:

1. Worker draft
2. Reviewer critique
3. Apply patch / refine (loop with cap)
4. Final answer emission

If altering logic:

- Keep termination conditions explicit (max iterations, no new critique, convergence heuristic)
- Preserve streaming semantics (surface intermediate reflections as distinct event blocks for UI clarity)
- Avoid embedding business logic in ChatAgent prompts—use structured controller logic where possible

---

## 5. Experimental Dynamic Workflow

The `_experimental_dynamic.py` module may:

- Adjust active agents based on task classification
- Introduce ephemeral specialized agents (e.g., summarizer) and retire them post-use
- Rebuild planning prompts mid-run when stall detected

When modifying:

| Requirement                           | Rationale                               |
| ------------------------------------- | --------------------------------------- |
| Provide feature flag / opt-in         | Avoid destabilizing default fleet       |
| Log adaptation decisions (callback)   | Debuggability + audit trail             |
| Avoid mutating original agent configs | Re-clone or shallow copy configurations |
| Cap expansion breadth                 | Prevent combinatorial explosion         |

---

## 6. Adding a New Workflow Variant

| Step | Action                               | Notes                                                      |
| ---- | ------------------------------------ | ---------------------------------------------------------- |
| 1    | Create `<name>.py`                   | Use concise snake_case name                                |
| 2    | Implement `create_<name>_workflow()` | Return object exposing `.run(task, **kwargs)`              |
| 3    | Add to `__init__.py` exports         | Maintain public API surface                                |
| 4    | Add CLI / API integration (optional) | Modify `cli/repl.py` or FastAPI endpoint mapping           |
| 5    | Document in root + this AGENTS.md    | Summarize capability & limitations                         |
| 6    | Add tests                            | Extend `tests/test_dynamic_workflow.py` or create new file |
| 7    | Provide fallback mode                | Users should recover to stable fleet on failure            |

---

## 7. API Surface Expectations

All workflow objects SHOULD:

| Method                                  | Purpose                                          |
| --------------------------------------- | ------------------------------------------------ |
| `run(task: str, **kwargs)`              | Execute full lifecycle; may stream via callbacks |
| `abort()` (optional)                    | Cooperative cancellation hook                    |
| `resume(checkpoint_id: str)` (optional) | Restore prior state when checkpointing supported |

Return value: Structured payload (dict / Pydantic) with at minimum `status`, `output` (final text or structured result), `metadata` (timings, iterations, tool usage). Keep additions backwards-compatible.

---

## 8. Checkpointing Integration

If a workflow supports checkpointing:

- Use `FileCheckpointStorage` or `InMemoryCheckpointStorage`
- Capture: iteration index, active plan, accumulated context, tool result cache
- Avoid serializing large raw model responses (store summaries)
- Provide `resume_from_checkpoint` param to `run()`

---

## 9. Reflection Pattern Guidelines

| Principle            | Implementation Hint                                          |
| -------------------- | ------------------------------------------------------------ |
| Deterministic cap    | `max_reflection_rounds` in config or function arg            |
| Divergence detection | Hash of last answer vs refined answer; stop if unchanged     |
| Critique quality     | If critique length < threshold → consider converged          |
| Patch safety         | Reviewer must not introduce unvalidated external assumptions |
| Streaming clarity    | Emit worker / reviewer blocks with distinct roles            |

---

## 10. Observability Hooks

Workflow variants should leverage callback system (`fleet/callbacks.py`). Minimum recommended events:

| Event                     | When                                                      |
| ------------------------- | --------------------------------------------------------- |
| plan_creation             | Initial + replans                                         |
| progress_ledger           | After each major phase                                    |
| tool_call                 | Around each tool execution                                |
| final_answer              | On successful termination                                 |
| reflection_cycle (custom) | At each reviewer critique (emit: round, critique summary) |

Add custom events conservatively—UI and CLI must tolerate absence.

---

## 11. Error & Stall Handling

| Scenario               | Strategy                                                 |
| ---------------------- | -------------------------------------------------------- |
| Tool failure           | Retry limited (1–2) then escalate to manager critique    |
| Repeated empty plans   | Trigger full replan or terminate with diagnostic message |
| Reflection oscillation | Detect answer hash loop (A→B→A) and short-circuit        |
| Approval timeout       | Mark operation aborted; surface partial output clearly   |

---

## 12. Testing Workflow Variants

| Test Type                   | Focus                                                 |
| --------------------------- | ----------------------------------------------------- |
| Unit (controller functions) | Plan merging, critique application, termination flags |
| Integration                 | End-to-end `.run()` with mocked client + tools        |
| Regression                  | Ensure output schema stable across refactors          |
| Performance (optional)      | Iteration count vs task complexity                    |

Use existing patterns in `tests/test_dynamic_workflow.py` & `tests/test_magentic_fleet.py` as reference. Mock `OpenAIResponsesClient` to avoid cost.

---

## 13. Adding CLI Support

If exposing new workflow through CLI:

1. Add mode flag or keyword (e.g., `--workflow reflection`).
2. Map flag → factory in `cli/repl.py`.
3. Provide descriptive banner text on start.
4. Ensure fallbacks to default fleet on unsupported mode.

FastAPI exposure: add route (POST) under `/v1/workflow/<name>` returning streaming SSE using existing response event schema.

---

## 14. Performance Considerations

| Aspect               | Concern                 | Guidance                                           |
| -------------------- | ----------------------- | -------------------------------------------------- |
| Reflection rounds    | Unbounded cost          | Enforce max + early convergence checks             |
| Adaptive agent spawn | Explosion of contexts   | Pool / reuse or cap count                          |
| Tool re-execution    | Redundant expensive ops | Cache recent tool outputs keyed by normalized args |
| Checkpoint size      | Large JSON growth       | Store summaries + references instead of raw logs   |

---

## 15. Extension Safety Checklist

Before merging a new workflow variant:

- ✅ No hardcoded model names
- ✅ Configurable iteration limits
- ✅ Uses callbacks, not `print()` for observability
- ✅ Returns structured result with `status` + `output`
- ✅ Tool + approval flows unchanged or documented
- ✅ Tests added / updated

---

## 16. Common Pitfalls

| Pitfall                                            | Prevention                                         |
| -------------------------------------------------- | -------------------------------------------------- |
| Embedding orchestration logic in agent prompt only | Keep control flow explicit in Python wrapper       |
| Silent termination                                 | Always emit final callback with status code        |
| Ignoring stalled state                             | Use stall counters (configurable)                  |
| Non-idempotent resume                              | Serialize enough state to replay deterministically |

---

## 17. Quick Dev Commands

```bash
# Focus dynamic workflow tests
uv run pytest tests/test_dynamic_workflow.py -v

# Run reflection-specific API tests (example)
uv run pytest -k reflection -v

# Grep for workflow exports
grep -R "create_.*workflow" -n src/agenticfleet/workflows
```

---

## 18. Versioning & Stability

| Label        | Meaning                                            |
| ------------ | -------------------------------------------------- |
| Stable       | Backwards-compatible; part of public API           |
| Experimental | May change without semver bump (underscore prefix) |
| Deprecated   | Announce in root `AGENTS.md` before removal        |

---

## 19. References

- Fleet builder: `../fleet/fleet_builder.py`
- Core Magentic: `../fleet/magentic_fleet.py`
- Callbacks: `../fleet/callbacks.py`
- Approval: `../core/approval.py`
- Root guide: `../../AGENTS.md`
- Dynamic tests: `../../../tests/test_dynamic_workflow.py`

---

**End – Workflows AGENTS.md**
