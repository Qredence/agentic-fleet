# AgenticFleet – Azure Cosmos DB NoSQL Data Model

This document defines the **concrete Cosmos DB logical model** for AgenticFleet, derived from `cosmosdb_requirements.md`.

The goals are:

- Same schema & logic for all AgenticFleet deployments.
- Optimized for:
  - Multi-agent workflow execution history.
  - Long-term agent memory (vector-friendly).
  - DSPy self-improvement (examples + optimization runs).
  - Result caching.
- Aligned with Azure Cosmos DB NoSQL best practices (high-cardinality partition keys, mostly single-partition critical paths, controlled cross-partition queries).

> **Note**: This file is _schema-level_. Provisioning steps for your specific account are documented at the end.

---

## 1. Database

- **Database ID**: `agentic-fleet`
- **API**: Azure Cosmos DB for NoSQL (Core SQL API)

All containers below live in this database.

---

## 2. Containers Overview

| Container ID            | Purpose                                        | Partition Key | Typical Item Count (per user) | Notes                                                     |
| ----------------------- | ---------------------------------------------- | ------------- | ----------------------------- | --------------------------------------------------------- |
| `workflowRuns`          | End-to-end workflow runs + events + quality    | `/workflowId` | 10s–1000s                     | Primary OLTP path for execution history.                  |
| `agentMemory`           | Long-term per-user/agent memory items          | `/userId`     | 100s–100k                     | Vector-friendly, top-k retrieval.                         |
| `dspyExamples`          | DSPy supervisor training/eval examples         | `/userId`     | 10s–10k                       | Mirrors `supervisor_examples.json`.                       |
| `dspyOptimizationRuns`  | DSPy optimization / compilation sessions       | `/userId`     | 10s–100s                      | Stores optimizer configs + program snapshots.             |
| `cache`                 | Cached workflow/query results with TTL         | `/cacheKey`   | 10s–10k                       | Short-lived, TTL-based.                                   |
| `workflowRunSegments`\* | Optional overflow for very large workflow runs | `/workflowId` | Rare                          | Only used if `workflowRuns` risk hitting 2 MB item limit. |

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

### 3.2 `agentMemory` – Long-Term Memory

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

### 3.3 `dspyExamples` – DSPy Supervisor Examples

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

  "task": "Analyze error logs and suggest a fix for failing tests in the workflow supervisor.",
  "team": ["planner", "coder", "verifier"],
  "available_tools": ["HostedCodeInterpreterTool"],
  "context": "Tests failing in test_supervisor_handoffs.py after recent refactor.",
  "assigned_to": ["planner", "coder", "verifier"],
  "mode": "sequential",
  "tool_requirements": {
    "planner": [],
    "coder": ["HostedCodeInterpreterTool"],
    "verifier": ["HostedCodeInterpreterTool"]
  },

  "labels": {
    "difficulty": "medium",
    "category": "dev_workflow"
  },

  "createdAt": "2025-11-17T09:55:00.000Z"
}
```

#### 3.3.2 Indexing guidance

- Index: `userId`, `dataset`, `mode`, `team`, `labels.category`, `createdAt`.
- Common queries:
  - Fetch subsets by `dataset` & `mode` for DSPy optimizers.
  - Filter by `labels.category` when training specialized behaviors.

---

### 3.4 `dspyOptimizationRuns` – DSPy Optimization Sessions

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

### 3.5 `cache` – Cached Workflow/Query Results

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

### 3.6 `workflowRunSegments` (Optional) – History Overflow

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

- `COSMOSDB_ACCOUNT_ENDPOINT` – your Cosmos DB account endpoint (e.g., `https://cosmos-fleet.documents.azure.com:443/`).
- `COSMOSDB_ACCOUNT_KEY` – **primary or secondary key** for the account (store securely; rotate if leaked).
- `COSMOSDB_DATABASE_ID` – `agentic-fleet`.

In development, put **only placeholder values** in `.env` checked into source control, and override them in your local, secret `.env.local` or via environment settings in your hosting platform.

> **Important**: The connection string you shared in chat contains a live account key. Treat it as compromised and rotate it in Azure Portal or via CLI before using this schema in production.

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

In your AgenticFleet backend, configure the Cosmos client to use the environment variables above. For example, in Python pseudocode (do **not** hard-code secrets):

```python
import os
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

endpoint = os.environ.get("AZURE_COSMOS_ENDPOINT")
database_id = os.environ.get("AZURE_COSMOS_DATABASE", "agentic-fleet")
use_managed_identity = os.environ.get("AZURE_COSMOS_USE_MANAGED_IDENTITY")

if not endpoint:
  raise RuntimeError("AZURE_COSMOS_ENDPOINT is required to connect to Cosmos DB.")

if use_managed_identity:
  credential = DefaultAzureCredential()
else:
  key = os.environ.get("AZURE_COSMOS_KEY")
  if not key:
    raise RuntimeError(
      "AZURE_COSMOS_KEY is required when managed identity authentication is disabled."
    )
  credential = key

client = CosmosClient(endpoint, credential=credential)
db = client.get_database_client(database_id)

workflow_runs = db.get_container_client("workflowRuns")
agent_memory = db.get_container_client("agentMemory")
dspy_examples = db.get_container_client("dspyExamples")
opt_runs = db.get_container_client("dspyOptimizationRuns")
cache = db.get_container_client("cache")
```

> This connection setup can be wrapped in a small repository/DAO layer that maps the logical entities (`WorkflowRun`, `AgentMemoryItem`, etc.) to Cosmos documents using the schemas above.

---

## 6. Summary

- Requirements in `cosmosdb_requirements.md` are now fully mapped to a concrete Cosmos DB data model.
- The design supports:
  - Multi-agent workflow runs with embedded events and quality data.
  - Long-term, vector-friendly agent memory per user.
  - DSPy routing/quality training via reusable examples.
  - Self-improvement tracking via optimization runs.
  - TTL-based caching for expensive computations.
- Provisioning steps and environment variable recommendations are provided while keeping secrets out of source control.

This gives you a stable, repeatable Cosmos DB schema that matches AgenticFleet's DSPy-enhanced, self-improving multi-agent design and can be used across all deployments, including your `cosmos-fleet` account.
