# Operations Runbook (Production)

This document captures **operational** guidance for running AgenticFleet in production-like environments (API + WebSocket).

## Production checklist

- **DSPy artifacts**
  - Run `agentic-fleet optimize` during build/release.
  - Set `dspy.require_compiled: true` in `src/agentic_fleet/config/workflow_config.yaml` so startup fails fast if artifacts are missing.
- **Runtime compilation**
  - Avoid runtime/background compilation for production deployments (initialize workflows with `compile_dspy=False`).
- **Secrets / env**
  - Set `OPENAI_API_KEY` (required).
  - If using Tavily search: set `TAVILY_API_KEY`.
  - For tracing export: configure `tracing.*` and/or `APPLICATIONINSIGHTS_CONNECTION_STRING`.
- **Filesystem expectations**
  - `.var/` is local runtime state (logs/caches/history/checkpoints). For multi-replica deployments, mount a persistent volume or move stateful components to shared storage.

## Capacity controls (backpressure)

### Concurrent workflow limit

The API applies a coarse concurrency cap via `WorkflowSessionManager(max_concurrent=...)` (see `agentic_fleet/api/lifespan.py`).

- When the limit is reached, new workflow sessions are rejected with **HTTP 429**.
- Tune via settings (`AppSettings.max_concurrent_workflows`).

### WebSocket runtime guardrails

The WebSocket chat service enforces basic runtime bounds (timeouts, heartbeats) to prevent idle connections from consuming resources indefinitely.

## Rate limiting & quotas

AgenticFleet does not currently implement a full per-user/token bucket rate limiter in-process. Recommended production patterns:

- **Edge rate limiting**: enforce per-IP and per-user limits in your ingress (NGINX, Envoy, API Gateway, Front Door, etc.).
- **Request sizing**: cap request body sizes and message lengths.
- **Quota policies**: enforce daily/monthly token budgets at the gateway layer.

### LLM retry behavior

LiteLLM retry is configured to fail fast on rate limits in the API lifespan (see `agentic_fleet/api/lifespan.py`).

## Scaling

### Horizontal scaling

To run multiple replicas safely:

- Use a shared conversation store (avoid local file-only persistence if you need cross-replica continuity).
- Avoid relying on local `.var/` state for anything correctness-critical unless it is on shared storage.
- Ensure checkpoint storage is compatible with your scaling model (local disk checkpoints are per-replica unless shared).

### WebSocket considerations

WebSocket sessions are stateful. If you run multiple replicas:

- Use sticky sessions (same client → same replica) **or**
- Store required state (threads/checkpoints) in shared backends so reconnects can land on any replica.

## Concurrency note: per-request reasoning effort

`SupervisorWorkflow._apply_reasoning_effort` may mutate agent client state when applying a per-request override. To prevent cross-request interference under concurrent WebSocket load, the WebSocket service initializes a **fresh SupervisorWorkflow per socket session**.

If you introduce new shared singletons (e.g., globally shared agents), re-evaluate this risk.

## Observability

- **Logs**: JSON logs are on by default; set `LOG_JSON=0` for human-readable logs.
- **Tracing**: Configure `tracing.enabled` + `tracing.otlp_endpoint` for local collectors; use Azure Monitor export when configured.
- **History**: executions are recorded under `.var/logs/execution_history.jsonl` by default.
