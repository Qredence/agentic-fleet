# AgenticFleet Overview

## What is AgenticFleet?

AgenticFleet is a production-oriented **agentic workflow framework**: it helps you route a user request to the
right mix of specialized agents and tools, execute the work, and return a high-quality final answer with
traceable logs and history.

At its core, AgenticFleet combines:

- **DSPy** for structured reasoning, routing decisions, progress/quality evaluation, and offline optimization.
- **Microsoft agent-framework** for reliable agent execution, tool invocation, and orchestration mechanics.

## What problems does it solve?

AgenticFleet is designed for teams building systems where a single LLM call is not enough:

- Multi-step tasks that need **planning + execution + verification**
- Tool-using assistants (web search, code execution, MCP bridges)
- Workflows that must be **observable** (logs, traces, history) and tunable over time
- Systems that should run quickly for simple prompts but still scale up to complex requests

## Typical use cases

### 1) Internal “Ops Copilot” / Engineering assistant

- Triage incidents, draft postmortems, summarize logs, propose mitigations
- Generate PR descriptions, release notes, and migration checklists

### 2) Research + synthesis pipelines

- Time-sensitive research (when a web-search tool is available)
- Compare sources, extract key points, produce concise briefs

### 3) Data / analysis workflows

- Quick calculations, data transformations, and report drafts
- “Explain my results” or “find anomalies” style tasks (depending on enabled tools)

### 4) Documentation and knowledge workflows

- Turn rough notes into structured docs
- Maintain consistent style and completeness via quality scoring and iteration

### 5) Evaluation and self-improvement loops

- Use execution history to evaluate performance over time
- Harvest high-quality runs to improve routing/decision quality offline

## How it works (high level)

Most requests follow a 5-phase pipeline:

`analysis → routing → execution → progress → quality`

- **Analysis**: understand the request and constraints.
- **Routing**: choose the execution mode and agents/tools to use.
- **Execution**: run agents (delegated / sequential / parallel).
- **Progress**: decide if the task is complete or needs another iteration.
- **Quality**: score the output, record missing items, and optionally refine (if enabled).

Simple prompts may take a fast-path to reduce latency.

For interactive sessions, AgenticFleet also supports:

- **Multi-turn continuity**: follow-up turns in the same conversation are executed with thread/history context.
- **Human-in-the-loop (HITL)**: workflows can pause on request events until a user responds.
- **Checkpoint resume**: interrupted runs can be resumed using agent-framework checkpoint semantics (resume requires a `checkpoint_id`).

## What you get out of the box

- CLI (`agentic-fleet`) for running tasks and dev servers
- YAML config (`config/workflow_config.yaml`) for models, routing, timeouts, and tool/agent settings
- Runtime artifacts under `.var/` (logs, JSONL history, evaluation outputs, caches)
- Developer docs in `docs/` (architecture, tracing, optimization, testing)

## Where to go next

- Start here: `docs/users/getting-started.md`
- Configure behavior: `docs/users/configuration.md`
- Day-to-day usage: `docs/users/user-guide.md`
- Commands at a glance: `docs/guides/quick-reference.md`
- Architecture details: `docs/developers/architecture.md`
