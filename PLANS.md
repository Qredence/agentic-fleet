# WebSocket Migration Plan

## Replace SSE with WebSocket Communication for Chat UI

**Status**: Implemented (2025-12-03)
**Branch**: feat/uxui

### Goal

Migrate from Server-Sent Events (SSE) to WebSocket-based bidirectional communication, enabling better connection management, reliable cancellation, and future extensibility (binary data, bidirectional messaging).

### Decisions

| Question             | Decision                                      | Rationale                                                                                                 |
| -------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Connection lifecycle | New WebSocket per message (Option A)          | Simpler migration matching current SSE pattern; optimize to persistent connection later                   |
| Conversation context | Send in JSON message (Option A)               | Matches existing `ChatRequest` schema; no URL routing changes needed                                      |
| Error recovery       | Use `reconnecting-websocket` built-in backoff | Battle-tested library already in deps; configure `maxReconnectionDelay` and `reconnectionDelayGrowFactor` |

### Progress

- [x] Backend WebSocket hardening (`src/agentic_fleet/app/routers/streaming.py`)
  - Handshake timeout + structured error, explicit `connected` and `cancelled` events (StreamEventType additions)
  - Stream payload now mirrors terminal logs (`log_line`) and includes `workflow_id` for UI correlation
  - Cancel polling tightened to 250ms; all error paths use structured StreamEvents with UI hints
- [x] Frontend streaming + UI responsiveness
  - `useChat` now updates deltas/steps immediately (no batching) and handles `connected/cancelled` events
  - Removed the Live Terminal Log panel per latest UX request; stream types still carry `log_line` for future telemetry use
  - Stream event types aligned in `src/frontend/src/api/types.ts` (log_line/workflow_id support)
- [ ] Stream reliability (DONE/heartbeat) — planned in ExecPlan below
- [ ] Routing light-mode, caching, and telemetry — planned in ExecPlan below
- [ ] Validation
  - Run `make test` (backend) and `make test-frontend` / `npm test` in `src/frontend` after any further edits

### Notes / Follow-ups

- Consider moving to a persistent WebSocket per session with ping/pong if long-lived sessions become common.
- If we adjust stream schema again, keep `api/types.ts` and `useChat` in sync and note changes here.

---

# ExecPlan: Accelerate & Harden AgenticFleet Streaming (v0.1)

**Goal**: Cut perceived latency and prevent “never-ending” streams while reducing token/tool waste on simple queries.

## Scope

- Stream reliability: guaranteed `RESPONSE_COMPLETED` + `DONE`, heartbeat/timeout, front-end stop conditions.
- Routing light-mode: minimal agent set for simple tasks; skip heavy phases when not needed.
- Web/tool efficiency: query caching for Tavily; schema validation to avoid tool drops.
- Observability: phase/timing metadata in stream events.

## Work Packages

1. **Stream Reliability**
   - Backend: emit DONE (or ERROR) once per run; heartbeat ping & idle timeout; cancellation updates status.
   - Frontend: handle DONE/ERROR/timeout to clear loading; show stalled-state fallback.
   - Tests: contract test for start→done, cancel timing.
2. **Routing Light-Mode**
   - Heuristic/classifier: if intent=factoid/short, run minimal pipeline (skip writer/reviewer/generator; single agent).
   - Cap supersteps and tool fan-out in light-mode; config flag + metrics.
3. **Caching & Tool Hygiene**
   - Cache Tavily/web results by normalized query+TTL; short-circuit duplicates.
   - Enforce tool JSON schema; drop/flag unsupported tools before dispatch.
4. **Telemetry**
   - Attach phase durations and tool timings to StreamEvent.data; log SLAs.
   - Optional UI badges for phase time + tool count.

## Deliverables

- Code patches for backend WS stream and routing toggle.
- Frontend updates for DONE/heartbeat handling and stall UI.
- Tests: stream schema contract, cancel timing, cache hit/miss unit.
- Docs: PLANS.md entry (this) + AGENTS.md note on light-mode flag and new env/config.

## Milestones

- M1 (1–2 days): Stream reliability fixes + frontend handling + contract test.
- M2 (1–2 days): Light-mode heuristic, config toggle, telemetry fields.
- M3 (1 day): Caching + tool schema enforcement.
- Wrap: docs + perf snapshot (start-to-first-token, start-to-done).

## Expected Outcomes

- Start-to-first-UI-update under 1s for simple prompts; no lingering spinners (DONE/ERROR always delivered).
- Token/tool spend reduced on factoid/short asks via light-mode routing.
- Fewer tool-call warnings and retries through schema enforcement; repeat queries served faster via cache hits.
- Phase/tool timing visible for debugging and SLA tracking; easier to spot bottlenecks.

## Risks & Mitigations

- Misrouted light-mode on complex asks → confidence threshold + fallback to full pipeline.
- Cache staleness → short TTL, include source timestamp, bypass on explicit “fresh” flag.
