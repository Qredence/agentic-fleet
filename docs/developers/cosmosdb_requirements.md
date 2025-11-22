# Azure Cosmos DB NoSQL Modeling Session

## Application Overview

- **Domain**: Multi-Agent AI Workflow System (AgenticFleet)
- **Key Entities**: Tasks, Agents, Workflows, Users, Execution History, DSPy Training Examples, Quality Assessments, Cached Results, Tool Registry, Configuration
- **Business Context**: DSPy-enhanced agent framework system using Microsoft agent-framework with Azure OpenAI for orchestrated multi-agent workflows. Supports delegated, sequential, and parallel execution modes with quality assessment and refinement loops.
- **Scale**: Individual developer/researcher usage, 1-5 concurrent workflows max, locally runnable with personal Azure Cosmos DB resources
- **Geographic Distribution**: Single region deployment (user's preferred Azure region)

### Volume Calculation Framework

**Usage Pattern**: Individual developer/researcher workflows

- **Concurrent Workflows**: 1-5 maximum
- **Daily Workflows**: ~10-50 workflows per day (estimated)
- **Workflow Duration**: 30 seconds to 10 minutes per workflow
- **Peak Usage**: Bursts during development/testing sessions

## Access Patterns Analysis

| Pattern # | Description                                    | RPS (peak/avg) | Type  | Attributes Needed                                             | Latency SLO  | Consistency        | Expected Result Size                   | Document Size Band             | Design Considerations                                                                        | Status |
| --------- | ---------------------------------------------- | -------------- | ----- | ------------------------------------------------------------- | ------------ | ------------------ | -------------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------- | ------ |
| 1         | Create new workflow execution                  | 1 / <0.1       | Write | workflowId, userId, task, agents, config, timestamp           | P95 < 200 ms | Strong / session   | 1 document per request                 | Medium (5–50 KB)               | Point write with workflowId as partition key; low contention                                 | ⏳     |
| 2         | Log agent execution step/event                 | 5 / ~1         | Write | workflowId, agentId, stepId, result, timestamp                | P95 < 200 ms | Session / eventual | 1 small document or subdocument append | Small (1–5 KB per step)        | Append-only pattern; co-locate with workflow to avoid cross-partition writes                 | ⏳     |
| 3         | Query workflow execution history for dashboard | 2 / ~0.5       | Read  | workflowId, userId, time window                               | P95 < 100 ms | Session            | 1–20 documents per query               | Medium (5–100 KB each)         | Single-partition query by workflowId (primary); cross-partition by userId + time acceptable  | ⏳     |
| 4         | Store/update DSPy training examples            | 0.5 / <<0.1    | Write | exampleId, task, routing, quality scores, team, mode          | P95 < 250 ms | Strong / session   | 1 document per write                   | Small–medium (2–20 KB)         | Document replacement; low write rate                                                         | ⏳     |
| 5         | Query DSPy examples for optimization           | 1 / <<0.5      | Read  | task patterns, team, mode, quality thresholds                 | P95 < 200 ms | Session            | 10–200 documents                       | Small–medium (2–20 KB)         | Cross-partition queries acceptable at low scale; consider partitioning by team/mode          | ⏳     |
| 6         | Store agent memory/knowledge                   | 2 / ~0.5       | Write | userId, agentId, content, embedding vector, metadata          | P95 < 250 ms | Eventual           | 1 document per write                   | Medium (2–10 KB text + vector) | Vector-friendly structure; partition by userId; optional TTL for stale memory                | ⏳     |
| 7         | Retrieve agent memory for context              | 3 / ~1         | Read  | userId, agentId, semantic query/embedding                     | P95 < 150 ms | Session            | Top-k (5–20) documents                 | Medium (2–10 KB text + vector) | Efficient vector search (Cosmos DB vector index or external store); filter by userId/agentId | ⏳     |
| 8         | Cache workflow results                         | 1 / ~0.2       | Write | cacheKey (task hash), userId, workflowId, result summary, TTL | P95 < 150 ms | Eventual           | 1 document per write                   | Medium (2–20 KB)               | TTL-based cleanup; partition by cacheKey; cache hits dominate reads                          | ⏳     |
| 9         | Query cached results                           | 2 / ~0.5       | Read  | cacheKey                                                      | P95 < 50 ms  | Session            | 0–1 document                           | Medium (2–20 KB)               | Point read by cacheKey; high cache hit rate desired                                          | ⏳     |

## Legacy System Analysis (When Applicable)

_Will be documented if modernizing from existing system_

## Entity Relationships Deep Dive

### Core identities

- **User / Workspace**
  - Logical owner of workflows, memory, and optimization runs (e.g., a developer's local AgenticFleet instance).
  - Key: `userId` (or `workspaceId` for multi-tenant scenarios).

### Execution & history

- **WorkflowRun**
  - Represents one end-to-end supervisor run (task + multi-agent execution + quality loop).
  - Natural key: `workflowId` (UUID).
  - References: `userId` (owner/workspace), optional `projectId` / `runTag` for grouping.

- **WorkflowEvents (embedded)**
  - Individual agent steps, tool calls, intermediate results, progress updates.
  - Modeled as an **embedded array** inside `WorkflowRun.events[]` so the full history for a run is co-located.
  - Cardinality: `WorkflowRun (1) → WorkflowEvent (N)`.

- **QualityEvaluations (embedded)**
  - Quality scores, judge decisions, refinement requests, and final evaluation.
  - Modeled as `WorkflowRun.quality` and `WorkflowRun.judge_evaluations[]`.
  - Cardinality: `WorkflowRun (1) → QualityEvaluation (N)`.

### DSPy optimization & training

- **DSPySupervisorExample**
  - Training example used by DSPy optimizers and routing.
  - Fields mirror `supervisor_examples.json` (task, team, available_tools, context, assigned_to, mode, tool_requirements).
  - Independent entity (not owned by a single workflow).
  - Relationships:
    - `User/Workspace (1) → DSPySupervisorExample (N)` via `userId`.
    - `DSPyOptimizationRun (1) → DSPySupervisorExample (N)` via `exampleIds[]` for train/eval sets.

- **DSPyOptimizationRun**
  - Represents a compilation/optimization session (e.g., GEPA, BootstrapFewShot).
  - Stores optimizer config, metrics progression, and references to datasets.
  - Relationships:
    - `User/Workspace (1) → DSPyOptimizationRun (N)`.
    - `DSPyOptimizationRun (1) → DSPyProgramSnapshot (1)` (embedded or referenced).

- **DSPyProgramSnapshot (embedded)**
  - Serializable state of an optimized program: signature, demos, instructions, LM config.
  - Stored as an embedded object inside `DSPyOptimizationRun.program_snapshot`.

### Long-term agent memory

- **AgentMemoryItem**
  - Small, semantically meaningful memory unit (fact, preference, experience, reminder) inspired by Mem0 and `dspy.History`.
  - Keys:
    - `userId` (owner),
    - `agentId` (e.g. `researcher`, `analyst`),
    - optional `memoryType` (`fact`, `preference`, `experience`, `reminder`),
    - `memoryId` (UUID).
  - Relationships:
    - `User (1) → AgentMemoryItem (N)` (primary identifying relationship).
    - `Agent (1) → AgentMemoryItem (N)` via `agentId`.
    - Optional weak link `WorkflowRun (1) → AgentMemoryItem (N)` via `sourceWorkflowId`.

### Caching & configuration

- **CacheEntry**
  - Stores a computed result keyed by a deterministic `cacheKey`.
  - Links back to `userId` and optionally `workflowId`.
  - Relationships: `User (1) → CacheEntry (N)`; `WorkflowRun (0..1) → CacheEntry (N)` via `workflowId`.

- **ToolRegistryEntry / Configuration** (low-churn)
  - Static-ish records that describe tools, agents, and workflow configuration for reproducibility.
  - Usually stored as configuration files in the repo; in Cosmos we only need minimal metadata: `configVersion`, `agentRoster`, `toolVersionHashes`.
  - Relationship: referenced from `WorkflowRun.configSnapshot` if persisted.

## Enhanced Aggregate Analysis

### WorkflowRun aggregate (execution + events + quality)

- **Access correlation**
  - Dashboard/inspection views almost always need the full workflow: task, routing, events, quality, judge evaluations, and final result.
  - Very few queries need an individual event in isolation.
- **Identifying relationship**
  - Events and quality evaluations are meaningless without the parent `workflowId` and its context.
- **Choice**
  - Model as a **single document aggregate** per `workflowId` with nested arrays for events (`events[]`), quality (`quality`), judge evaluations (`judge_evaluations[]`), and analysis/routing.
- **Justification**
  - Simplifies reads: a single point read serves most UX and debugging scenarios.
  - Matches the current `logs/execution_history.jsonl` shape, easing migration.
  - Write rate is low and concurrency per workflow is effectively 1, so document updates per step are acceptable.
- **Risks & mitigations**
  - Risk: very long-running workflows could approach the 2 MB document limit.
    - Mitigation: enforce practical limits on retained events per run; optionally spill excess events into a secondary `WorkflowRunSegments` container if ever needed.

### AgentMemoryItem aggregate (long-term memory)

- **Access correlation**
  - Memory retrieval is typically top-k semantic search for a given `userId` (+ optional `agentId` or `memoryType`).
  - We rarely need all memories for a user at once.
- **Identifying relationship**
  - Memory is owned by a user and optionally associated with a specific agent.
- **Choice**
  - Model **one document per memory item**, each containing text, embedding vector, metadata, and provenance (`sourceWorkflowId`).
  - Partition by `userId`.
- **Justification**
  - Plays nicely with vector search (Cosmos DB vector indexes or external vector DB).
  - Supports fine-grained TTL or importance-based pruning.
  - Aligns with Mem0-style memory units and `dspy.History` snapshots.

### DSPySupervisorExample aggregate (training examples)

- **Access correlation**
  - Optimizers consume batches of examples filtered by task pattern, team, mode, or tool availability.
  - Individual examples are occasionally edited but mostly append-only.
- **Identifying relationship**
  - Examples belong to a user/workspace and a logical dataset (e.g., `supervisor_routing_examples`).
- **Choice**
  - Model as **one document per example**, with fields mirroring `supervisor_examples.json` and a `dataset`/`source` tag.
- **Justification**
  - Simple, flexible filtering.
  - Examples can be reused across optimization runs; we avoid duplicating them into each `DSPyOptimizationRun`.

### DSPyOptimizationRun aggregate (self-improvement sessions)

- **Access correlation**
  - When inspecting optimization, we want optimizer config, metrics progression, final program snapshot, and references to datasets together.
- **Identifying relationship**
  - Tied to a `userId`/workspace and a specific optimizer type (`GEPA`, `MIPROv2`, etc.).
- **Choice**
  - Model as **one document per optimization run** containing:
    - `optimizerType`, `optimizerConfig`,
    - `trainExampleIds[]`, `evalExampleIds[]`,
    - `metricProgression[]`,
    - `program_snapshot` (embedded DSPy program state).
- **Justification**
  - Mirrors MLflow-style parent runs while staying self-contained.
  - Low write volume; mostly append-only metrics during the run, then read-mostly.

### CacheEntry aggregate (workflow/result cache)

- **Access correlation**
  - Cache is accessed by `cacheKey`; we rarely need to join multiple cache records.
- **Identifying relationship**
  - Optionally linked to a `workflowId` and `userId`, but the primary identity is `cacheKey`.
- **Choice**
  - Model as **one document per cache key**, storing input hash, result summary, optional full result, and TTL.
- **Justification**
  - Clean TTL semantics using container-level TTL.
  - Simple point reads/writes with predictable RU usage.

## Container Consolidation Analysis

| Root Aggregate      | Related Entity                     | Access Overlap                                                             | Consolidation Decision                                                     | Notes                                                                                                                                                                     |
| ------------------- | ---------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| WorkflowRun         | WorkflowEvents, QualityEvaluations | ~100% of queries that touch events/quality also need core workflow fields  | **Consolidate** – embed events and quality structures inside `WorkflowRun` | Reduces joins and cross-partition lookups; keep per-run document under 2 MB with pragmatic limits on history length.                                                      |
| WorkflowRun         | CacheEntry                         | Low–medium (some UIs may show "cached result" next to workflow)            | **Do not consolidate** – keep `CacheEntry` separate                        | Cache has different TTL and access patterns; using `cacheKey` as partition key is more natural than `workflowId`. Link via `workflowId` when available.                   |
| WorkflowRun         | AgentMemoryItem                    | Low (memory mostly reused across workflows, retrieved via semantic search) | **Do not consolidate** – separate `AgentMemoryItem` container              | Memory is long-lived, often shared across workflows, and optimized for vector search; coupling it to individual workflow documents would create large, uneven aggregates. |
| DSPyOptimizationRun | DSPySupervisorExample              | Medium (runs reference many examples; examples reused across runs)         | **Do not consolidate** – reference examples by ID                          | Keeps examples reusable and avoids duplicating them into every optimization run; enables separate lifecycle policies.                                                     |
| AgentMemoryItem     | CacheEntry                         | Very low                                                                   | **Do not consolidate**                                                     | Different purposes and TTL semantics; no meaningful shared access pattern.                                                                                                |

## Design Considerations (Subject to Change)

- **Hot Partition Concerns**:
  - `WorkflowRun` is partitioned by `workflowId`, giving naturally high cardinality and low risk of hot partitions.
  - `AgentMemoryItem` partitions by `userId`; per-user memory volume is expected to stay well below the 20 GB logical partition limit.
- **Large fan-out / many physical partitions**:
  - Current scale (1–5 concurrent workflows, tens of runs/day) keeps physical partition count low.
  - Cross-partition fan-out is mainly from analytical queries over many workflows or training examples; acceptable at current scale.
- **Cross-Partition Query Costs**:
  - Most critical paths (read/write of a specific workflow, cache lookup, user-specific memory retrieval) are single-partition.
  - Training/evaluation queries over `DSPySupervisorExample` may span partitions but are batch/offline and low RPS.
- **Indexing Strategy**:
  - Keep default indexing for `WorkflowRun` but consider excluding large nested arrays if RU costs become an issue.
  - For `AgentMemoryItem`, enable vector index on the embedding field and index `userId`, `agentId`, `memoryType`, `createdAt`.
  - For `DSPySupervisorExample` and `DSPyOptimizationRun`, index `dataset`, `team`, `mode`, `optimizerType`, and timestamps for filtering.
- **Multi-Document Opportunities**:
  - If some workflows approach the 2 MB limit, introduce a `WorkflowRunSegments` container keyed by `workflowId` + `segmentIndex` to offload older events while keeping the current design for normal runs.
- **Multi-Entity Query Patterns**:
  - Primary cross-entity patterns:
    - "Show workflow + its cached result" → join `WorkflowRun` and `CacheEntry` on `workflowId` (rare, acceptable as two point reads).
    - "Show workflow + relevant long-term memories" → vector search in `AgentMemoryItem` filtered by `userId` + optional `sourceWorkflowId`.
- **Denormalization Ideas**:
  - Embed small, immutable config snapshots (agent roster, tool list, thresholds) into `WorkflowRun.configSnapshot` for full reproducibility.
  - Store summary statistics (duration, quality score, failure reasons) redundantly at the root of `WorkflowRun` to avoid scanning nested arrays for common queries.
- **CQRS using Change Feed or GSI**:
  - Potential to use Change Feed on `WorkflowRun` to populate secondary projections (e.g., time-series analytics, per-agent performance dashboards) without impacting OLTP queries.
  - Similarly, Change Feed on `AgentMemoryItem` could drive downstream analytics or external vector indexes if needed.
- **Global Distribution**:
  - Current assumption is single-region per user.
  - If AgenticFleet is later offered as a hosted multi-tenant service, consider hierarchical partition keys combining `tenantId` + `workflowId` and enable multi-region writes for low-latency global access.

## Validation Checklist

- [x] Application domain and scale documented
- [x] All entities and relationships mapped
- [x] Aggregate boundaries identified based on access patterns
- [x] Identifying relationships checked for consolidation opportunities
- [x] Container consolidation analysis completed
- [x] Every access pattern has: RPS (avg/peak), latency SLO, consistency level, expected result size, document size band
- [x] Write pattern exists for every read pattern (and vice versa) unless USER explicitly declines
- [x] Hot partition risks evaluated
- [x] Consolidation framework applied; candidates reviewed
- [x] Design considerations captured (subject to final validation)
