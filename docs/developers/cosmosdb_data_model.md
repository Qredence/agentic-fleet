# AgenticFleet – Azure Cosmos DB NoSQL Data Model

This document defines the **concrete Cosmos DB logical model** for AgenticFleet, derived from `cosmosdb_requirements.md`.

---

## Design Philosophy & Approach

### Core Design Principles Applied

1. **Aggregate-Oriented Design**: Data is modeled around natural aggregates that are frequently accessed together, minimizing cross-partition queries for the critical OLTP paths.

2. **High-Cardinality Partition Keys**: Every container uses partition keys with naturally high cardinality (`workflowId`, `userId`, `cacheKey`) to ensure even data distribution and avoid hot partitions.

3. **Single-Partition Critical Paths**: The most frequent access patterns (workflow reads, cache lookups, memory retrieval) are designed as single-partition operations for predictable low latency (<100ms P95).

4. **Identifying Relationships**: Child entities (events, quality evaluations) that cannot exist without their parent are embedded or co-located using the parent's partition key, eliminating cross-partition joins.

5. **Strategic Embedding vs. Referencing**:
   - **Embed** when: >90% access correlation, bounded size, related update patterns
   - **Reference** when: Independent lifecycle, unbounded growth, different access patterns

### Design Goals

| Goal                               | How Achieved                                               |
| ---------------------------------- | ---------------------------------------------------------- |
| Same schema across all deployments | Config-driven containers with consistent naming            |
| Optimized workflow execution       | Single-document aggregate with embedded events             |
| Vector-friendly memory             | Dedicated container with vector index support              |
| DSPy self-improvement              | Separate containers for examples vs. runs (reusability)    |
| TTL-based caching                  | Dedicated cache container with container-level TTL         |
| Low RU cost at small scale         | 400 RU/s autoscale per container, single-partition queries |

---

## Aggregate Design Decisions

### Decision 1: WorkflowRun as Single-Document Aggregate

**Analysis:**

- Access correlation between workflow metadata, events, and quality: **~100%**
- Dashboard/inspection views almost always need the complete picture
- Write concurrency per workflow: effectively 1 (single supervisor run)
- Average document size: 5-50KB; max expected: 500KB-1MB

**Decision:** Single document aggregate embedding `events[]`, `quality`, and `judge_evaluations[]`

**Justification:**

- Single point read serves 95%+ of UX and debugging scenarios
- Matches existing `.var/logs/execution_history.jsonl` shape for easy migration
- Low write rate means document-level updates are cost-effective
- Avoids N+1 query problem when loading workflow details

**Risk Mitigation:** For workflows exceeding 1.5MB, overflow to `workflowRunSegments` container.

### Decision 2: AgentMemoryItem as Individual Documents

**Analysis:**

- Access correlation: Low (top-k semantic search, not full user memory)
- Growth pattern: Unbounded (users accumulate memories over time)
- Update pattern: Append-mostly with occasional importance decay

**Decision:** One document per memory item, partitioned by `userId`

**Justification:**

- Enables fine-grained TTL and importance-based pruning
- Compatible with Cosmos DB vector indexes for semantic search
- Aligns with Mem0-style memory units and `dspy.History` snapshots
- Avoids bloating user documents with unbounded memory arrays

### Decision 3: Separate Examples from Optimization Runs

**Analysis:**

- Access correlation: Medium (runs reference examples, but examples are reused)
- Examples have different lifecycle (long-lived training data)
- Optimization runs are audit records of compilation sessions

**Decision:** Two containers: `dspyExamples` (reusable) + `dspyOptimizationRuns` (sessions)

**Justification:**

- Examples can be shared across multiple optimization runs without duplication
- Different retention policies (examples permanent, runs may be pruned)
- Cleaner change feed semantics for each entity type
- Enables independent scaling if example corpus grows large

### Decision 4: Cache as Natural-Key Container

**Analysis:**

- Access pattern: Point read/write by deterministic `cacheKey`
- No need for user-scoped queries (cache is content-addressed)
- Short-lived entries with automatic cleanup

**Decision:** Dedicated `cache` container with `/cacheKey` partition key and TTL enabled

**Justification:**

- Perfect for point reads (1 RU per read)
- TTL handles automatic cleanup without application logic
- Decoupled from workflow lifecycle (cache may outlive or expire before workflow)

### Decision 5: Conversation as Single-Document Aggregate with Embedded Messages

**Analysis:**

- Access correlation between conversation metadata and messages: **~100%**
- Every follow-up question needs full conversation history for context
- Agent routing decisions depend on understanding the entire thread
- Average conversation: 10-50 messages; max expected: 100-200 messages

**Decision:** Single document aggregate embedding `messages[]` array with inline quality metadata per message

**Justification:**

- **Single point read for full context**: Agent routing and follow-up handling need entire history (1 RU vs 10-50 RU for separate message queries)
- **Matches chat UX**: Frontend always loads complete conversation threads
- **Context injection**: The `messages[]` array maps directly to chat completion API message arrays
- **Aligns with existing implementation**: Matches `Conversation` and `Message` Pydantic models in `src/agentic_fleet/models/conversations.py`
- **Write amplification acceptable**: Human-paced interactions naturally throttle writes; document size stays manageable

**Risk Mitigation:**

- For conversations exceeding 500 messages or ~1MB, implement sliding window retention
- Archive older messages or replace with LLM-generated summary as system message
- Optional `conversationArchive` container for extremely long threads

---

## 1. Database

- **Database ID**: `agentic-fleet`
- **API**: Azure Cosmos DB for NoSQL (Core SQL API)

All containers below live in this database.

---

## 2. Containers Overview

| Container ID            | Purpose                                         | Partition Key     | Typical Item Count (per user) | Notes                                                     |
| ----------------------- | ----------------------------------------------- | ----------------- | ----------------------------- | --------------------------------------------------------- |
| `workflowRuns`          | End-to-end workflow runs + events + quality     | `/workflowId`     | 10s–1000s                     | Primary OLTP path for execution history.                  |
| `conversations`         | Multi-turn chat sessions with embedded messages | `/conversationId` | 10s–100s                      | Full thread context for follow-ups and agent routing.     |
| `agentMemory`           | Long-term per-user/agent memory items           | `/userId`         | 100s–100k                     | Vector-friendly, top-k retrieval.                         |
| `dspyExamples`          | DSPy supervisor training/eval examples          | `/userId`         | 10s–10k                       | Mirrors `supervisor_examples.json`.                       |
| `dspyOptimizationRuns`  | DSPy optimization / compilation sessions        | `/userId`         | 10s–100s                      | Stores optimizer configs + program snapshots.             |
| `cache`                 | Cached workflow/query results with TTL          | `/cacheKey`       | 10s–10k                       | Short-lived, TTL-based.                                   |
| `workflowRunSegments`\* | Optional overflow for very large workflow runs  | `/workflowId`     | Rare                          | Only used if `workflowRuns` risk hitting 2 MB item limit. |

`workflowRunSegments` is **optional**; you only need it if some workflows become extremely large. The core design assumes `workflowRuns` is sufficient for typical usage.

---

## 3. Container Schemas

### 3.1 `workflowRuns` – Workflow Execution History

- **Container ID**: `workflowRuns`
- **Partition key**: `/workflowId`
- **TTL**: _Off_ by default (history is long-lived). You may add a default TTL later for cost control.

Each document represents a **single supervisor run**, including:

- Task metadata.
- DSPy analysis & routing.
- Events (agent steps, tool calls, intermediate messages).
- Quality evaluations & judge output.
- Final answer and summary.

#### 3.1.1 Example document

```json
{
  "id": "wf_01HZYR7VQ23G8X9T3C5KJ7A1B2",
  "workflowId": "wf_01HZYR7VQ23G8X9T3C5KJ7A1B2",
  "userId": "user_123",
  "projectId": "agenticfleet-demo",
  "runTag": "console-run-2025-11-17-01",

  "task": {
    "input": "Research 2025 AI trends for cloud inference.",
    "createdAt": "2025-11-17T10:15:23.512Z",
    "metadata": {
      "source": "cli",
      "cliCommand": "agentic-fleet run -m 'Research 2025 AI trends' --verbose"
    }
  },

  "dspy_analysis": {
    "complexity": "medium",
    "needs_web_search": true,
    "search_query": "2025 AI cloud inference trends",
    "available_tools": ["TavilySearchTool", "HostedCodeInterpreterTool"],
    "notes": "Research + analysis + report synthesis"
  },

  "routing": {
    "mode": "sequential",
    "assigned_team": ["researcher", "analyst", "writer", "reviewer"],
    "subtasks": [
      {
        "step": 1,
        "agent": "researcher",
        "description": "Collect up-to-date sources on AI inference trends.",
        "tool_requirements": ["TavilySearchTool"]
      },
      {
        "step": 2,
        "agent": "analyst",
        "description": "Summarize quantitative trends and cost models.",
        "tool_requirements": ["HostedCodeInterpreterTool"]
      }
    ]
  },

  "events": [
    {
      "eventId": "ev_001",
      "timestamp": "2025-11-17T10:15:24.100Z",
      "agentId": "supervisor",
      "type": "analysis",
      "payload": {
        "message": "Task classified as research+analysis; routing to Researcher→Analyst→Writer→Reviewer."
      }
    },
    {
      "eventId": "ev_010",
      "timestamp": "2025-11-17T10:15:30.901Z",
      "agentId": "researcher",
      "type": "tool_call",
      "toolName": "TavilySearchTool",
      "toolInput": {
        "query": "2025 AI cloud inference trends",
        "num_results": 5
      },
      "toolOutputSummary": "Retrieved 5 recent articles on serverless and on-demand GPUs."
    }
  ],

  "quality": {
    "overallScore": 8.5,
    "dimensions": {
      "correctness": 8.0,
      "completeness": 9.0,
      "clarity": 8.0,
      "citations": 9.0
    },
    "refinementNeeded": false,
    "feedback": [
      "Good coverage of major providers.",
      "Could add more detail on pricing models."
    ]
  },

  "judge_evaluations": [
    {
      "round": 1,
      "timestamp": "2025-11-17T10:16:10.005Z",
      "score": 8.5,
      "reasoning": "Meets threshold for correctness and completeness.",
      "suggested_improvements": [
        "Add 1–2 concrete provider examples.",
        "Clarify trade-offs between managed and self-hosted inference."
      ]
    }
  ],

  "result": {
    "answer": "In 2025, AI inference in the cloud is dominated by on-demand GPU pools...",
    "format": "markdown",
    "tokens": {
      "prompt": 3124,
      "completion": 812
    }
  },

  "execution_summary": {
    "status": "succeeded",
    "durationSeconds": 52.4,
    "agentsUsed": ["researcher", "analyst", "writer", "reviewer"],
    "toolsUsed": ["TavilySearchTool", "HostedCodeInterpreterTool"],
    "startedAt": "2025-11-17T10:15:23.512Z",
    "completedAt": "2025-11-17T10:16:15.900Z"
  },

  "configSnapshot": {
    "workflowConfigVersion": "2025-11-01",
    "agents": ["researcher", "analyst", "writer", "reviewer"],
    "quality": {
      "judge_model": "gpt-5",
      "judge_threshold": 7.5,
      "max_refinement_rounds": 1
    }
  }
}
```

#### 3.1.2 Indexing guidance

- Leave **default indexing** on for convenience.
- If RU costs become high:
  - Exclude heavy nested arrays (`/events/*`, `/judge_evaluations/*`) from indexing.
  - Add composite indexes for common queries such as:
    - `userId` + `task.createdAt`
    - `userId` + `execution_summary.status`

---

### 3.2 `conversations` – Multi-Turn Chat Sessions

- **Container ID**: `conversations`
- **Partition key**: `/conversationId`
- **TTL**: _Off_ by default (conversations are user-valuable data). Optional TTL for auto-cleanup of inactive threads.

Each document represents a **complete conversation thread**, including:

- Conversation metadata (title, timestamps, owner).
- Full message history (user + assistant messages) for context preservation.
- Per-message quality metadata for evaluation tracking.
- Optional workflow references for provenance.

#### 3.2.1 Why Embedded Messages?

The conversation model embeds all messages in a single document because:

1. **Full context always needed**: When the agentic system processes a follow-up question, it needs the entire conversation history to understand context, previous decisions, and user preferences.
2. **Agent routing depends on history**: The DSPy routing modules use conversation history to make better decisions about which agents to involve.
3. **Single point read**: Loading a conversation for the UI or for agent context is always 1 RU (single point read by `conversationId`).
4. **Matches chat UX**: The frontend always loads and displays complete conversation threads.

#### 3.2.2 Example document

```json
{
  "id": "conv_01HZYR8ABC23G8X9T3C5KJ7A1B2",
  "conversationId": "conv_01HZYR8ABC23G8X9T3C5KJ7A1B2",
  "userId": "user_123",
  "title": "Research 2025 AI trends",
  "createdAt": "2025-11-17T10:15:23.512Z",
  "updatedAt": "2025-11-17T10:25:45.123Z",

  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "Research 2025 AI trends for cloud inference.",
      "author": null,
      "agentId": null,
      "workflowId": null,
      "createdAt": "2025-11-17T10:15:23.512Z",
      "qualityScore": null,
      "qualityFlag": null,
      "qualityPending": false,
      "qualityDetails": null
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "I'll research the 2025 AI inference trends. Before I dive deep, could you clarify:\n\n1. Are you interested in specific cloud providers (Azure, AWS, GCP) or a general overview?\n2. Should I focus on cost optimization, performance, or both?\n3. Do you need information about specific model types (LLMs, vision, multimodal)?",
      "author": "supervisor",
      "agentId": "supervisor",
      "workflowId": "wf_01HZYR7VQ23G8X9T3C5KJ7A1B2",
      "createdAt": "2025-11-17T10:15:30.100Z",
      "qualityScore": 8.5,
      "qualityFlag": "pass",
      "qualityPending": false,
      "qualityDetails": {
        "correctness": 8.0,
        "helpfulness": 9.0,
        "clarity": 8.5
      }
    },
    {
      "id": "msg_003",
      "role": "user",
      "content": "Focus on Azure and cost optimization for LLMs specifically.",
      "author": null,
      "agentId": null,
      "workflowId": null,
      "createdAt": "2025-11-17T10:20:15.200Z",
      "qualityScore": null,
      "qualityFlag": null,
      "qualityPending": false,
      "qualityDetails": null
    },
    {
      "id": "msg_004",
      "role": "assistant",
      "content": "Great, I'll focus on Azure's cost-optimized LLM inference options for 2025. Here's my analysis:\n\n## Azure AI Inference Cost Optimization in 2025\n\n### 1. Provisioned Throughput Units (PTUs)\n...",
      "author": "writer",
      "agentId": "writer",
      "workflowId": "wf_01HZYR7VQ23G8X9T3C5KJ7A1B3",
      "createdAt": "2025-11-17T10:25:45.123Z",
      "qualityScore": 9.0,
      "qualityFlag": "pass",
      "qualityPending": false,
      "qualityDetails": {
        "correctness": 9.0,
        "completeness": 9.0,
        "clarity": 9.0,
        "actionable": 9.0
      }
    }
  ],

  "metadata": {
    "messageCount": 4,
    "lastAgentId": "writer",
    "lastWorkflowId": "wf_01HZYR7VQ23G8X9T3C5KJ7A1B3",
    "tags": ["research", "azure", "ai-inference"]
  }
}
```

#### 3.2.3 Message Schema Reference

Each message in the `messages[]` array contains:

| Field            | Type    | Required | Description                                              |
| ---------------- | ------- | -------- | -------------------------------------------------------- |
| `id`             | string  | Yes      | Unique message ID (UUID)                                 |
| `role`           | string  | Yes      | `"user"`, `"assistant"`, or `"system"`                   |
| `content`        | string  | Yes      | Message text content                                     |
| `author`         | string  | No       | Human-readable author name (e.g., agent name)            |
| `agentId`        | string  | No       | ID of agent that generated the response                  |
| `workflowId`     | string  | No       | ID of workflow run that produced the response            |
| `createdAt`      | string  | Yes      | ISO 8601 timestamp                                       |
| `qualityScore`   | number  | No       | Overall quality score (0-10) after evaluation            |
| `qualityFlag`    | string  | No       | `"pass"`, `"fail"`, or `"pending"`                       |
| `qualityPending` | boolean | No       | Whether quality evaluation is still in progress          |
| `qualityDetails` | object  | No       | Detailed quality dimensions (correctness, clarity, etc.) |

#### 3.2.4 Size Management for Long Conversations

**Risk**: Very long conversations could approach the 2 MB document limit.

**Mitigation strategies** (in order of preference):

1. **Sliding window**: Keep only the last N messages (e.g., 100) in the main document. Archive older messages.
2. **Content summarization**: Replace older messages with an LLM-generated summary stored as a `"system"` message.
3. **Overflow container**: For extremely long threads, create a `conversationArchive` container and reference archived segments.

**Practical limits** (typical usage stays well under limits):

- Average message: 500-2000 characters (~0.5-2 KB)
- 100 messages × 2 KB = 200 KB (well under 2 MB)
- Very active conversations with 500 messages: ~1 MB (still safe)

#### 3.2.5 Indexing guidance

- Index: `userId`, `updatedAt`, `createdAt`, `metadata.tags`.
- **Exclude from indexing** if needed: `/messages/*/content` (large text), `/messages/*/qualityDetails/*`.
- Composite index for listing conversations: `userId` + `updatedAt` DESC.

---

### 3.3 `agentMemory` – Long-Term Memory

- **Container ID**: `agentMemory`
- **Partition key**: `/userId`
- **TTL**: Optional; you may set a default TTL for low-importance or stale memories, or manage TTL via per-item `ttl` values.

Each document is a single memory unit, aligned with Mem0-style and `dspy.History`-style memories.

#### 3.2.1 Example document

```json
{
  "id": "mem_01HZYS0X7C437WSFPPJ6QGW8KQ",
  "memoryId": "mem_01HZYS0X7C437WSFPPJ6QGW8KQ",
  "userId": "user_123",
  "agentId": "researcher",
  "memoryType": "preference",
  "content": "User prefers examples focused on Azure AI and cost-optimized inference.",
  "embedding": [0.0123, -0.0456, 0.0879],
  "metadata": {
    "source": "workflow",
    "sourceWorkflowId": "wf_01HZYR7VQ23G8X9T3C5KJ7A1B2",
    "createdAt": "2025-11-17T10:17:10.001Z",
    "importance": 0.9
  },
  "ttl": null
}
```

#### 3.2.2 Vector + filter queries

- Primary filters: `userId` (partition key), optional `agentId`, `memoryType`, `metadata.importance`.
- Vector similarity search over `embedding` using Cosmos DB vector index (or an external vector store if preferred).

#### 3.2.3 Indexing guidance

- Index scalar fields: `userId`, `agentId`, `memoryType`, `metadata.createdAt`, `metadata.importance`.
- Configure a **vector index** on `embedding` (Cosmos DB vector search).

---

### 3.4 `dspyExamples` – DSPy Supervisor Examples

- **Container ID**: `dspyExamples`
- **Partition key**: `/userId`
- **TTL**: Off (examples are long-lived training data).

Each document corresponds to a single DSPy supervisor example, similar to entries in `src/agentic_fleet/data/supervisor_examples.json`.

#### 3.3.1 Example document

```json
{
  "id": "ex_01HZYSAZ7V8KH3W3PM3N9DTHNQ",
  "exampleId": "ex_01HZYSAZ7V8KH3W3PM3N9DTHNQ",
  "userId": "user_123",
  "dataset": "supervisor_routing_examples",

  "task": "What is Gemini 3 Pro?",
  "team": "Researcher: search for 'Google Gemini 3 Pro AI model' to avoid confusion with other products\nWriter: summarize findings",
  "assigned_to": "Researcher,Writer",
  "mode": "sequential",
  "available_tools": "- TavilySearchTool (available to Researcher): Search the web for real-time information using Tavily. Provides accurate, up-to-date results with source citations. [Capabilities: web_search, real_time, citations]",
  "context": "Specific product query with potential ambiguity",
  "tool_requirements": ["TavilySearchTool"],

  "labels": {
    "difficulty": "medium",
    "category": "research"
  },

  "createdAt": "2025-11-17T09:55:00.000Z"
}
```

> **Note**: The schema mirrors entries in `src/agentic_fleet/data/supervisor_examples.json` with additional Cosmos-specific fields (`id`, `exampleId`, `userId`, `dataset`, `createdAt`).

#### 3.3.2 Indexing guidance

- Index: `userId`, `dataset`, `mode`, `team`, `labels.category`, `createdAt`.
- Common queries:
  - Fetch subsets by `dataset` & `mode` for DSPy optimizers.
  - Filter by `labels.category` when training specialized behaviors.

---

### 3.5 `dspyOptimizationRuns` – DSPy Optimization Sessions

- **Container ID**: `dspyOptimizationRuns`
- **Partition key**: `/userId`
- **TTL**: Off (optimization runs are valuable for audit & replay).

Each document captures one DSPy optimization/compilation session (e.g., GEPA, MIPROv2, BootstrapFewShot).

#### 3.4.1 Example document

```json
{
  "id": "opt_01HZYT3WJY08HH1EF7GZABXJ4F",
  "runId": "opt_01HZYT3WJY08HH1EF7GZABXJ4F",
  "userId": "user_123",

  "optimizerType": "GEPA",
  "optimizerConfig": {
    "metric": "semantic_f1",
    "auto": "light",
    "max_metric_calls": 64
  },

  "trainExampleIds": [
    "ex_01HZYSAZ7V8KH3W3PM3N9DTHNQ",
    "ex_01HZYSAZ7V8KH3W3PM3N9DTHNR"
  ],
  "evalExampleIds": ["ex_01HZYSAZ7V8KH3W3PM3N9DTHNS"],

  "metricProgression": [
    {
      "round": 1,
      "metric": 0.72,
      "timestamp": "2025-11-17T08:15:00.000Z"
    },
    {
      "round": 2,
      "metric": 0.81,
      "timestamp": "2025-11-17T08:18:00.000Z"
    }
  ],

  "program_snapshot": {
    "signature": "question -> answer",
    "demos": [
      {
        "id": "demo_001",
        "input": "What is AgenticFleet?",
        "output": "AgenticFleet is a DSPy-enhanced multi-agent runtime built on Microsoft's agent-framework."
      }
    ],
    "lm": {
      "model": "gpt-5-mini",
      "temperature": 0.2
    }
  },

  "createdAt": "2025-11-17T08:10:00.000Z",
  "completedAt": "2025-11-17T08:20:00.000Z",
  "status": "succeeded"
}
```

#### 3.4.2 Indexing guidance

- Index: `userId`, `optimizerType`, `status`, `createdAt`, `completedAt`.
- Optional: composite index on `userId` + `createdAt` for listing runs by time.

---

### 3.6 `cache` – Cached Workflow/Query Results

- **Container ID**: `cache`
- **Partition key**: `/cacheKey`
- **TTL**: **On** with a default (e.g., 3600 seconds = 1 hour).

Each document is a cache entry keyed by a deterministic hash of the input (e.g., normalized task description + key flags).

#### 3.5.1 Example document

```json
{
  "id": "cache_01HZYTQ2VKFYDK7DE324QNRR7X",
  "cacheKey": "sha256:3d1c5f...",
  "userId": "user_123",
  "workflowId": "wf_01HZYR7VQ23G8X9T3C5KJ7A1B2",

  "request": {
    "task": "Research 2025 AI trends for cloud inference.",
    "options": {
      "depth": "summary",
      "include_sources": true
    }
  },

  "result": {
    "answerSummary": "In 2025, AI inference workloads increasingly use on-demand GPU pools...",
    "topSources": [
      "https://learn.microsoft.com/azure/ai",
      "https://aws.amazon.com/machine-learning/"
    ],
    "fullResultRef": null
  },

  "createdAt": "2025-11-17T10:16:16.000Z",
  "ttl": 3600
}
```

#### 3.5.2 Indexing guidance

- Primary usage is point reads/writes by `cacheKey` (partition key).
- Default indexing is fine; you may exclude `result` subtrees if RU becomes an issue for analytical queries.

---

### 3.7 `workflowRunSegments` (Optional) – History Overflow

Only needed if some workflow runs risk breaching the **2 MB item size limit**.

- **Container ID**: `workflowRunSegments`
- **Partition key**: `/workflowId`
- **TTL**: Off or long (segments are historical).

#### 3.6.1 Example document

```json
{
  "id": "wfseg_01HZYV9T0M6Z1R8PHMZ2T6H7J9",
  "workflowId": "wf_01HZYR7VQ23G8X9T3C5KJ7A1B2",
  "segmentIndex": 1,

  "events": [
    {
      "eventId": "ev_120",
      "timestamp": "2025-11-17T10:30:00.000Z",
      "agentId": "researcher",
      "type": "tool_call",
      "toolName": "TavilySearchTool",
      "toolInput": { "query": "..." },
      "toolOutputSummary": "..."
    }
  ],

  "createdAt": "2025-11-17T10:30:01.000Z"
}
```

The main `workflowRuns` document would then store only the most recent events plus a reference like:

```json
{
  "segments": {
    "hasOverflow": true,
    "maxSegmentIndex": 1
  }
}
```

---

## 4. Environment Variables (Recommended)

To avoid hard-coding secrets and account information, configure these environment variables in your AgenticFleet deployment:

### Required Variables

- `AGENTICFLEET_USE_COSMOS` – Set to `"1"`, `"true"`, `"yes"`, or `"on"` to enable Cosmos DB integration
- `AZURE_COSMOS_ENDPOINT` – Your Cosmos DB account endpoint (e.g., `https://cosmos-fleet.documents.azure.com:443/`)
- `AZURE_COSMOS_DATABASE` – Database ID (default: `agentic-fleet`)

### Authentication (choose one)

- `AZURE_COSMOS_KEY` – Primary or secondary key for key-based authentication (store securely; rotate if leaked)
- `AZURE_COSMOS_USE_MANAGED_IDENTITY` – Set to `"true"` to use Azure Managed Identity instead of keys

### Container Overrides (optional)

- `AZURE_COSMOS_WORKFLOW_RUNS_CONTAINER` – Override container name (default: `workflowRuns`)
- `AZURE_COSMOS_AGENT_MEMORY_CONTAINER` – Override container name (default: `agentMemory`)
- `AZURE_COSMOS_DSPY_EXAMPLES_CONTAINER` – Override container name (default: `dspyExamples`)
- `AZURE_COSMOS_DSPY_OPTIMIZATION_RUNS_CONTAINER` – Override container name (default: `dspyOptimizationRuns`)
- `AZURE_COSMOS_CACHE_CONTAINER` – Override container name (default: `cache`)

### User/Tenant Scoping

- `AGENTICFLEET_DEFAULT_USER_ID` or `AGENTICFLEET_USER_ID` – Default user ID for partitioning user-scoped data

In development, put **only placeholder values** in `.env` checked into source control, and override them in your local, secret `.env.local` or via environment settings in your hosting platform.

> **Security Note**: Never commit real credentials to source control. Use `.env.local` or environment variables in your deployment platform.

---

## 5. Provisioning in Your Cosmos Account

Given your account endpoint:

- `AccountEndpoint = https://cosmos-fleet.documents.azure.com:443/`

and its associated account key (kept secret), you can provision the schema above using Azure CLI or SDK code. Below is a CLI-oriented baseline.

### 5.1 Azure CLI – Create Database & Containers

First, log in and select the subscription that hosts the `cosmos-fleet` account.

```bash
az login
az account set --subscription <your-subscription-id>
```

Then create the database and containers (replace `<resource-group>` and `<account-name>` if different):

```bash
# Variables
RESOURCE_GROUP="<your-resource-group>"
ACCOUNT_NAME="cosmos-fleet"
DATABASE_ID="agentic-fleet"

# Create database (if not already present)
az cosmosdb sql database create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --name "$DATABASE_ID"

# workflowRuns
az cosmosdb sql container create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --database-name "$DATABASE_ID" \
  --name workflowRuns \
  --partition-key-path "/workflowId" \
  --throughput 400

# agentMemory
az cosmosdb sql container create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --database-name "$DATABASE_ID" \
  --name agentMemory \
  --partition-key-path "/userId" \
  --throughput 400

# dspyExamples
az cosmosdb sql container create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --database-name "$DATABASE_ID" \
  --name dspyExamples \
  --partition-key-path "/userId" \
  --throughput 400

# dspyOptimizationRuns
az cosmosdb sql container create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --database-name "$DATABASE_ID" \
  --name dspyOptimizationRuns \
  --partition-key-path "/userId" \
  --throughput 400

# cache (with TTL – configure TTL in portal or via indexing policy/TTL settings)
az cosmosdb sql container create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --database-name "$DATABASE_ID" \
  --name cache \
  --partition-key-path "/cacheKey" \
  --throughput 400

# conversations (for multi-turn chat threads)
az cosmosdb sql container create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --database-name "$DATABASE_ID" \
  --name conversations \
  --partition-key-path "/conversationId" \
  --throughput 400

# Optional overflow container
# az cosmosdb sql container create \
#   --resource-group "$RESOURCE_GROUP" \
#   --account-name "$ACCOUNT_NAME" \
#   --database-name "$DATABASE_ID" \
#   --name workflowRunSegments \
#   --partition-key-path "/workflowId" \
#   --throughput 400
```

You can later adjust throughput or enable autoscale based on your workload.

### 5.2 SDK Integration (High-Level)

In your AgenticFleet backend, Cosmos integration is already implemented in `src/agentic_fleet/utils/cosmos.py`. The module provides:

**Auto-enabled functions** (when `AGENTICFLEET_USE_COSMOS=true`):

- `mirror_execution_history(execution)` – Automatically called by `HistoryManager.save_execution()`
- `save_agent_memory_item(item)` – Persist long-term agent memory
- `query_agent_memory(user_id, agent_id, memory_type, limit)` – Retrieve agent memories
- `mirror_dspy_examples(examples, user_id, dataset)` – Mirror training examples
- `record_dspy_optimization_run(run)` – Persist optimization session metadata
- `mirror_cache_entry(cache_key, entry)` – Mirror cache metadata

**Example usage** (already integrated in the codebase):

```python
# HistoryManager automatically mirrors to Cosmos when enabled
from agentic_fleet.utils.history_manager import HistoryManager

manager = HistoryManager()
manager.save_execution(execution)  # Auto-mirrors to Cosmos if enabled

# Direct Cosmos operations for agent memory
from agentic_fleet.utils.cosmos import save_agent_memory_item, query_agent_memory

save_agent_memory_item({
    "content": "User prefers concise responses",
    "agentId": "writer",
    "memoryType": "preference",
})

memories = query_agent_memory(
    user_id="user_123",
    agent_id="writer",
    limit=10,
)
```

The integration is **best-effort**: if Cosmos is disabled or misconfigured, operations degrade gracefully without affecting the main execution path.

---

## 6. Access Pattern Mapping

### Solved Patterns – Reads

| Pattern # | Description                                | Container       | Cosmos DB Operation                                    | Implementation Notes                                                                      |
| --------- | ------------------------------------------ | --------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| 3         | Query workflow history for dashboard       | `workflowRuns`  | Point read by `workflowId` OR query by `userId` + time | Single-partition when workflowId known; cross-partition by userId acceptable at low scale |
| 5         | Query DSPy examples for optimization       | `dspyExamples`  | Query by `userId` + filters (dataset, mode, team)      | Cross-partition acceptable for batch offline queries                                      |
| 7         | Retrieve agent memory for context          | `agentMemory`   | Vector similarity + filter by `userId`, `agentId`      | Single-partition within user; leverage vector index                                       |
| 9         | Query cached results                       | `cache`         | Point read by `cacheKey`                               | 1 RU per hit; partition key = lookup key                                                  |
| 12        | Get conversation with full message history | `conversations` | Point read by `conversationId`                         | 1 RU per read; full thread context for follow-ups                                         |
| 13        | List user's conversations                  | `conversations` | Query by `userId` + `updatedAt` DESC                   | Cross-partition acceptable; return metadata only                                          |

### Solved Patterns – Writes

| Pattern # | Description                         | Container       | Cosmos DB Operation                                | Implementation Notes                                          |
| --------- | ----------------------------------- | --------------- | -------------------------------------------------- | ------------------------------------------------------------- |
| 1         | Create new workflow execution       | `workflowRuns`  | Upsert with `workflowId` as id + partition key     | Single point write; ~5 RU for 10KB document                   |
| 2         | Log agent execution step/event      | `workflowRuns`  | Partial update or full replace                     | Append to `events[]` array; use patch operations if available |
| 4         | Store/update DSPy training examples | `dspyExamples`  | Upsert by `exampleId`                              | Low frequency; ~5 RU per write                                |
| 6         | Store agent memory/knowledge        | `agentMemory`   | Create/upsert by `memoryId`                        | ~5 RU per write; include embedding vector                     |
| 8         | Cache workflow results              | `cache`         | Upsert by `cacheKey`                               | Set TTL on write; ~5 RU per write                             |
| 10        | Create new conversation thread      | `conversations` | Insert with `conversationId` as id + partition key | Single point write; ~3 RU for initial document                |
| 11        | Add message to conversation         | `conversations` | Replace or patch (append to `messages[]`)          | ~5-10 RU depending on document size                           |
| 14        | Update message quality score        | `conversations` | Patch specific message in `messages[]`             | Use partial update; ~3 RU                                     |

---

## 7. Hot Partition Analysis

| Container              | Partition Key     | Distribution Analysis                                       | Risk Level | Mitigation          |
| ---------------------- | ----------------- | ----------------------------------------------------------- | ---------- | ------------------- |
| `workflowRuns`         | `/workflowId`     | UUID per workflow = high cardinality, even distribution     | ✅ Low     | None needed         |
| `conversations`        | `/conversationId` | UUID per conversation = high cardinality, even distribution | ✅ Low     | None needed         |
| `agentMemory`          | `/userId`         | Per-user memories; individual users stay well under 20GB    | ✅ Low     | Monitor heavy users |
| `dspyExamples`         | `/userId`         | Training examples per user; bounded by practical limits     | ✅ Low     | None needed         |
| `dspyOptimizationRuns` | `/userId`         | Few runs per user                                           | ✅ Low     | None needed         |
| `cache`                | `/cacheKey`       | Content-addressed hash = perfect distribution               | ✅ Low     | None needed         |

**Calculation for workflowRuns:**

- Pattern #3 at 2 RPS distributed across unique workflowIds = <1 RPS per partition ✅
- No single workflow receives concentrated traffic

**Calculation for conversations:**

- Pattern #12 at 3 RPS distributed across unique conversationIds = <1 RPS per partition ✅
- Pattern #11 writes at 5 RPS average across all active conversations = negligible per-conversation load

**Calculation for agentMemory:**

- Pattern #7 at 3 RPS distributed across users
- Even a single active user at 3 RPS is well under 10,000 RU/s partition limit ✅

---

## 8. Trade-offs and Optimizations

### Trade-off 1: Embedded Events vs. Separate Event Documents

| Approach                       | Read Cost                | Write Cost        | Complexity | Decision    |
| ------------------------------ | ------------------------ | ----------------- | ---------- | ----------- |
| Embedded events in WorkflowRun | 1 RU (point read)        | 5-10 RU (replace) | Low        | ✅ Chosen   |
| Separate event documents       | 5-20 RU (query N events) | 5 RU per event    | Medium     | ❌ Rejected |

**Justification:** 95%+ of reads need full workflow context. Embedded approach saves RU on reads (1 vs 5-20) and simplifies code. Write amplification is acceptable given low concurrency per workflow.

### Trade-off 2: User-Partitioned Memory vs. Memory-ID Partitioned

| Approach              | Vector Search             | User Isolation  | Cross-User Analytics |
| --------------------- | ------------------------- | --------------- | -------------------- |
| Partition by userId   | ✅ Efficient within user  | ✅ Natural      | ❌ Cross-partition   |
| Partition by memoryId | ❌ Always cross-partition | ❌ No isolation | ✅ Single query      |

**Justification:** Memory retrieval is always user-scoped (you search _your_ agent's memory). User-partitioned design enables efficient single-partition vector search with natural data isolation.

### Trade-off 3: Denormalized Config Snapshot in WorkflowRun

**Decision:** Embed `configSnapshot` (agent roster, quality thresholds, tool versions) in each WorkflowRun.

**Trade-off:**

- Storage: ~1-2KB duplication per workflow
- Benefit: Full reproducibility without joining configuration tables
- Cost: Negligible at expected scale (1000 workflows × 2KB = 2MB)

**Justification:** Configuration changes rarely, but reproducibility is critical for debugging and audit. Embedding eliminates temporal consistency issues.

### Trade-off 4: Separate Cache Container vs. Embedded in WorkflowRun

| Approach                 | Cache Hit                    | TTL Management         | Storage Efficiency                |
| ------------------------ | ---------------------------- | ---------------------- | --------------------------------- |
| Separate cache container | 1 RU point read              | ✅ Container-level TTL | Deduplication across workflows    |
| Embedded in WorkflowRun  | 1 RU (part of workflow read) | ❌ Manual cleanup      | Duplication if same result cached |

**Justification:** Cache entries have different lifecycle (short TTL) and access patterns (lookup by content hash, not workflow). Separate container enables automatic TTL cleanup and content-addressed deduplication.

### Trade-off 5: Embedded Messages in Conversation vs. Separate Message Documents

| Approach                          | Read Cost                  | Write Cost        | Context Retrieval          | Complexity |
| --------------------------------- | -------------------------- | ----------------- | -------------------------- | ---------- |
| Embedded messages in Conversation | 1 RU (point read)          | 5-15 RU (replace) | ✅ Full thread in one read | Low        |
| Separate message documents        | 5-50 RU (query N messages) | 5 RU per message  | ❌ Multiple queries needed | Medium     |

**Decision:** Embed messages in the conversation document.

**Justification:**

- **Context is king**: When the agentic system processes a follow-up question or routes to agents, it needs the entire conversation history. A single point read (1 RU) vs querying potentially 20-100 messages (10-50 RU) is a significant cost saving.
- **Matches chat UX**: The frontend always loads complete conversations for display.
- **Aligns with existing models**: The `Conversation` and `Message` Pydantic models already use this embedded structure.
- **Write amplification acceptable**: Conversations are interactive (human-paced), so writes are naturally throttled. Even with 100 messages, document size stays under 200KB.

**Risk Mitigation:**

- For very long conversations (500+ messages), implement sliding window or summarization.
- Archive older messages to `conversationArchive` container if needed.

---

## 9. Cost Estimates

### RU Consumption (Monthly Projection)

Based on access patterns from requirements (individual developer usage):

| Operation            | RPS (avg) | RU/op | RU/s | Monthly RU | Est. Cost/mo |
| -------------------- | --------- | ----- | ---- | ---------- | ------------ |
| Create workflow      | 0.1       | 10    | 1    | 2.6M       | $0.02        |
| Log events (updates) | 1         | 10    | 10   | 26M        | $0.21        |
| Read workflow        | 0.5       | 1     | 0.5  | 1.3M       | $0.01        |
| Store memory         | 0.5       | 5     | 2.5  | 6.5M       | $0.05        |
| Vector search memory | 1         | 10    | 10   | 26M        | $0.21        |
| Cache read           | 0.5       | 1     | 0.5  | 1.3M       | $0.01        |
| Cache write          | 0.2       | 5     | 1    | 2.6M       | $0.02        |
| DSPy example queries | 0.5       | 20    | 10   | 26M        | $0.21        |
| Create conversation  | 0.1       | 5     | 0.5  | 1.3M       | $0.01        |
| Add message          | 1         | 10    | 10   | 26M        | $0.21        |
| Read conversation    | 1         | 1     | 1    | 2.6M       | $0.02        |
| List conversations   | 0.2       | 10    | 2    | 5.2M       | $0.04        |

**Total estimated throughput:** ~50 RU/s average → **400 RU/s provisioned** per container is sufficient

**Monthly cost estimate:** ~$7-20/month for individual developer usage with serverless or 400 RU/s autoscale per container

### Storage Projection

| Container            | Avg Doc Size | Docs/month   | Monthly Growth | 12-mo Projection |
| -------------------- | ------------ | ------------ | -------------- | ---------------- |
| workflowRuns         | 30 KB        | 500          | 15 MB          | 180 MB           |
| conversations        | 50 KB        | 50           | 2.5 MB         | 30 MB            |
| agentMemory          | 5 KB         | 2000         | 10 MB          | 120 MB           |
| dspyExamples         | 3 KB         | 100          | 0.3 MB         | 4 MB             |
| dspyOptimizationRuns | 10 KB        | 20           | 0.2 MB         | 2 MB             |
| cache                | 10 KB        | 1000 (TTL'd) | ~5 MB steady   | 5 MB             |

**Total 12-month storage:** ~340 MB → Storage cost negligible (~$0.09/month)

---

## 10. Global Distribution Strategy

### Current Design: Single Region

- **Primary region:** User's preferred Azure region (configured via deployment)
- **Consistency level:** Session (default) for most operations
- **Multi-region writes:** Not enabled (single developer usage)

### Future Multi-Tenant Considerations

If AgenticFleet evolves to a hosted multi-tenant service:

1. **Hierarchical Partition Keys:** Consider `tenantId` + `userId` + `workflowId` for `workflowRuns`
2. **Multi-region writes:** Enable for global low-latency access
3. **Conflict resolution:** Last-writer-wins for cache; custom resolver for memory merges
4. **Regional failover:** Automatic failover with Azure Traffic Manager

---

## 11. Validation Results ✅

- [x] **Reasoned step-by-step through design decisions** – Applied aggregate-oriented design, identifying relationships, and strategic embedding based on access correlation analysis ✅
- [x] **Aggregate boundaries clearly defined** – WorkflowRun (embedded), Conversation (embedded messages), AgentMemory (individual), DSPyExamples (individual), Cache (individual) ✅
- [x] **Every access pattern solved** – All 14 patterns from requirements mapped to container operations ✅
- [x] **Cross-partition queries eliminated for critical paths** – Workflow reads, conversation reads, cache lookups, and user-scoped memory are single-partition ✅
- [x] **All containers documented with full justification** – Partition key rationale, document types, and indexing strategy for each (6 core containers + 1 optional) ✅
- [x] **Hot partition analysis completed** – All containers use high-cardinality keys with even distribution ✅
- [x] **Cost estimates provided** – Monthly RU and storage projections calculated ✅
- [x] **Trade-offs explicitly documented** – 5 major trade-offs analyzed with cost/benefit reasoning ✅
- [x] **Global distribution strategy detailed** – Single-region current, multi-tenant future considerations ✅
- [x] **Cross-referenced against requirements** – All entities, relationships, and access patterns from `cosmosdb_requirements.md` addressed ✅
- [x] **Conversation/thread context preservation** – Full message history embedded for follow-up questions and agent routing ✅

---

## 12. Summary

- Requirements in `cosmosdb_requirements.md` are now fully mapped to a concrete Cosmos DB data model.
- The design supports:
  - **Multi-agent workflow runs** with embedded events and quality data (single-document aggregate)
  - **Multi-turn conversation threads** with embedded messages for context preservation across follow-ups
  - **Long-term, vector-friendly agent memory** per user (individual documents with vector index)
  - **DSPy routing/quality training** via reusable examples (separate from optimization runs)
  - **Self-improvement tracking** via optimization runs with embedded program snapshots
  - **TTL-based caching** for expensive computations (content-addressed, automatic cleanup)
- **Key design wins:**
  - 95%+ of critical operations are single-partition (1 RU reads, predictable latency)
  - Full conversation context available in single read for agent routing and follow-up handling
  - No hot partition risks due to high-cardinality partition keys
  - Estimated monthly cost: $7-20 for individual developer usage
  - Clean migration path from existing `.var/logs/` and `.var/data/` JSON files
- Provisioning steps and environment variable recommendations are provided while keeping secrets out of source control.

This gives you a stable, repeatable Cosmos DB schema that matches AgenticFleet's DSPy-enhanced, self-improving multi-agent design with full conversational context and can be used across all deployments.

---

## 13. Complementary Architecture: Azure AI Search + Foundry IQ (Agentic RAG)

While Cosmos DB handles **transactional data** (workflows, conversations, agent memory), **Azure AI Search with Foundry IQ** provides **enterprise-grade agentic retrieval** for grounding agents on knowledge bases.

### Why Foundry IQ for AgenticFleet?

| Capability              | Cosmos DB (Current)           | Azure AI Search + Foundry IQ                     |
| ----------------------- | ----------------------------- | ------------------------------------------------ |
| Agent memory retrieval  | Vector index on `agentMemory` | ✅ Superior: Semantic ranker + reflective search |
| Knowledge base / RAG    | Not supported                 | ✅ Native: Knowledge bases with answer synthesis |
| Multi-source federation | Manual implementation         | ✅ Automatic: Up to 10 knowledge sources         |
| Web grounding           | External tool needed          | ✅ Built-in: Bing Grounding API                  |
| Query decomposition     | Agent must handle             | ✅ Automatic: Sub-query planning                 |
| Citation-backed answers | Manual                        | ✅ Native: Inline citations                      |

### Foundry IQ Key Concepts

```
┌─────────────────────────────────────────────────────────────────┐
│                    FOUNDRY IQ ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌─────────────────────────────────────┐   │
│  │ AgenticFleet │────▶│      Knowledge Base (super tool)    │   │
│  │    Agent     │     │  - retrieval_reasoning_effort       │   │
│  └──────────────┘     │  - answer_synthesis mode            │   │
│                       │  - retrieval_instructions           │   │
│                       └───────────────┬─────────────────────┘   │
│                                       │                          │
│              ┌────────────────────────┼───────────────────────┐  │
│              ▼                        ▼                       ▼  │
│  ┌─────────────────┐   ┌─────────────────┐   ┌───────────────┐  │
│  │ Knowledge Source│   │ Knowledge Source│   │Knowledge Source│ │
│  │ (Azure Blob)    │   │ (SharePoint)    │   │ (Web/Bing)    │  │
│  └────────┬────────┘   └────────┬────────┘   └───────┬───────┘  │
│           │                      │                    │          │
│           ▼                      ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Azure AI Search Index                          ││
│  │  - Semantic ranker (L2)                                     ││
│  │  - Semantic classifier (L3) - new SLM for RAG tasks         ││
│  │  - Vector search + hybrid ranking                           ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Retrieval Reasoning Effort Levels

| Level       | Query Planning | Federation          | Reflective Search | Answer Synthesis | Use Case                                          |
| ----------- | -------------- | ------------------- | ----------------- | ---------------- | ------------------------------------------------- |
| **Minimal** | ❌             | All sources at once | ❌                | ❌               | Simple queries, lowest latency                    |
| **Low**     | ✅             | Source selection    | ❌                | ✅               | Balanced latency/quality                          |
| **Medium**  | ✅             | Source selection    | ✅ (1 iteration)  | ✅               | Complex queries, highest quality (+36% relevance) |

### Integration Pattern for AgenticFleet

#### Option A: Knowledge Base as Agent Tool (Recommended)

Register the Foundry IQ Knowledge Base as a tool available to AgenticFleet agents:

```python
# src/agentic_fleet/tools/foundry_iq.py
from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseRetrievalRequest,
    KnowledgeBaseMessage,
    KnowledgeBaseMessageTextContent,
    SearchIndexKnowledgeSourceParams,
    KnowledgeRetrievalLowReasoningEffort,
)
from azure.identity import DefaultAzureCredential

class FoundryIQTool:
    """Agentic retrieval tool using Azure AI Search Knowledge Base."""

    def __init__(
        self,
        search_endpoint: str,
        knowledge_base_name: str,
        knowledge_source_name: str,
    ):
        self.credential = DefaultAzureCredential()
        self.client = KnowledgeBaseRetrievalClient(
            endpoint=search_endpoint,
            knowledge_base_name=knowledge_base_name,
            credential=self.credential,
        )
        self.knowledge_source_name = knowledge_source_name

    async def retrieve(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        reasoning_effort: str = "low",  # minimal, low, medium
    ) -> dict:
        """
        Retrieve grounded information using agentic retrieval.

        Returns:
            {
                "answer": str,  # Synthesized answer with citations
                "references": list,  # Source documents
                "activity": list,  # Query decomposition steps
            }
        """
        messages = []
        if conversation_history:
            for msg in conversation_history:
                messages.append(
                    KnowledgeBaseMessage(
                        role=msg["role"],
                        content=[KnowledgeBaseMessageTextContent(text=msg["content"])]
                    )
                )

        messages.append(
            KnowledgeBaseMessage(
                role="user",
                content=[KnowledgeBaseMessageTextContent(text=query)]
            )
        )

        request = KnowledgeBaseRetrievalRequest(
            messages=messages,
            knowledge_source_params=[
                SearchIndexKnowledgeSourceParams(
                    knowledge_source_name=self.knowledge_source_name,
                    include_references=True,
                    include_reference_source_data=True,
                )
            ],
            include_activity=True,
            retrieval_reasoning_effort=KnowledgeRetrievalLowReasoningEffort,
        )

        result = self.client.retrieve(retrieval_request=request)

        return {
            "answer": result.response[0].content[0].text if result.response else None,
            "references": [r.as_dict() for r in result.references] if result.references else [],
            "activity": [a.as_dict() for a in result.activity] if result.activity else [],
        }
```

#### Option B: MCP Integration with Foundry Agents

Connect AgenticFleet to Foundry Agent Service via MCP (Model Context Protocol):

```python
# The knowledge base exposes an MCP endpoint that agents can call
# Create a project connection in Foundry pointing to the KB's mcp_endpoint
# Then use AIProjectClient to create agents with MCP tools

from azure.ai.projects import AIProjectClient

project_client = AIProjectClient(endpoint=project_endpoint, credential=credential)

# Agent automatically has access to knowledge base via MCP tool
agent = project_client.agents.create(
    model="gpt-5-mini",
    instructions="Use the knowledge base to answer questions about AgenticFleet documentation.",
    tools=[mcp_tool],  # MCP connection to knowledge base
)
```

### Environment Variables for Foundry IQ

```bash
# Azure AI Search
AZURE_SEARCH_ENDPOINT="https://<search-service>.search.windows.net"
AZURE_SEARCH_KNOWLEDGE_BASE_NAME="agenticfleet-kb"
AZURE_SEARCH_KNOWLEDGE_SOURCE_NAME="agenticfleet-docs-ks"

# Azure OpenAI (for reasoning in knowledge base)
AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-5-mini"

# Optional: Foundry Project (for MCP integration)
AZURE_FOUNDRY_PROJECT_ENDPOINT="https://<resource>.services.ai.azure.com/api/projects/<project>"
```

### When to Use Each System

| Data Type                          | Store                     | Reason                                       |
| ---------------------------------- | ------------------------- | -------------------------------------------- |
| Workflow execution history         | Cosmos DB `workflowRuns`  | OLTP, single-partition reads, audit trail    |
| Conversation threads               | Cosmos DB `conversations` | OLTP, full thread context needed for routing |
| Agent short-term memory            | Cosmos DB `agentMemory`   | User-scoped, per-agent, simple retrieval     |
| **Knowledge base / documentation** | **Azure AI Search KB**    | Semantic search, multi-source federation     |
| **Enterprise data grounding**      | **Azure AI Search KB**    | SharePoint, OneLake, Blob, web sources       |
| **Complex RAG queries**            | **Azure AI Search KB**    | Query decomposition, reflective search       |
| DSPy training examples             | Cosmos DB `dspyExamples`  | Batch queries, reusable across runs          |
| Cache                              | Cosmos DB `cache`         | TTL-based, content-addressed                 |

### Performance Benchmarks (from Microsoft)

| Query Difficulty   | Minimal | Low | Medium | Improvement |
| ------------------ | ------- | --- | ------ | ----------- |
| Easy (NQ)          | 97      | 98  | 98     | +1%         |
| Medium (HotPot)    | 79      | 88  | 91     | +16%        |
| Hard (SEC-Open)    | 67      | 84  | 90     | +33%        |
| Very Hard (Frames) | 54      | 80  | 86     | **+60%**    |
| **Average**        | 59      | 74  | 80     | **+36%**    |

### Provisioning Azure AI Search for Agentic Retrieval

```bash
# Prerequisites
# 1. Azure AI Search service (Basic tier or higher for semantic ranker)
# 2. Azure OpenAI deployment (gpt-4o-mini, gpt-5-mini, etc.)
# 3. Semantic ranker enabled on search service

# Install preview SDK
pip install azure-search-documents --pre

# See: https://learn.microsoft.com/azure/search/search-get-started-agentic-retrieval
```

### Migration Path

1. **Phase 1 (Current)**: Cosmos DB for all data, basic vector search on `agentMemory`
2. **Phase 2**: Add Azure AI Search KB for documentation/knowledge grounding
3. **Phase 3**: Migrate complex RAG from agent memory to Knowledge Base
4. **Phase 4**: Full Foundry IQ integration with MCP tools

This hybrid architecture gives AgenticFleet:

- **Cosmos DB**: Fast OLTP for operational data (workflows, conversations, DSPy)
- **Azure AI Search + Foundry IQ**: Enterprise-grade agentic retrieval for knowledge grounding
