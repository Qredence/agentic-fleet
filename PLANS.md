# ExecPlan: AgenticFleet DSPy & Tooling Hardening (2025-11-20)

## Goal

Improve routing accuracy, latency, and self-improvement for AgenticFleet by making Tavily MCP the default web-search path, tightening time-sensitive enforcement, enabling better parallel routing, and capturing richer operational metrics.

## Success Criteria (initial)

- p50 end-to-end latency unchanged or lower after changes; p90 not worse by >10% on benchmark tasks.
- Time-sensitive tasks always route with `tavily_search` in tool plan when the key is present.
- Parallel routing chosen when multiple agents/subtasks are emitted; no delegations with >1 assignee.
- History entries capture tool/routing metadata for self-improvement to consume.

## Work Items

1. Routing & tool-awareness
   - Feed real tool metadata (capabilities, latency hints) into DSPy routing.
   - Detect time-sensitive tasks and enforce `tavily_search` + Researcher assignment.
   - Normalize delegations with multiple assignees into parallel execution.
2. Self-improvement & history hooks
   - Ensure executions record routing/tool context so `SelfImprovementEngine` can mine edge cases.
3. Docs & ergonomics
   - Document new defaults (Tavily MCP required for current events) and parallel mode usage in `AGENTS.md`.

4. PoT resilience
   - Track the last Program of Thought failure message so we can annotate history/self-improvement data.
   - When PoT fails due to invalid Python, fall back to the plain ChatAgent result while surfacing a short notice so CLI users see the fallback reason.
   - Log the failure metadata (strategy, error) with each execution so SelfImprovementEngine can target similar tasks.

## Notes

- Tavily is available via `TAVILY_API_KEY` in `.env`; avoid OpenAI hosted web search per user request.
- Keep changes incremental; no behavior regressions for existing standard mode.
