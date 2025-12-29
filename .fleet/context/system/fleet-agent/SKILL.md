---
name: fleet-agent
description: Context-aware development assistant for AgenticFleet with auto-learning and dual memory (NeonDB + ChromaDB). Handles development workflows with intelligent context management.
focus: development, context-management, pattern-learning, code-analysis
triggers:
  - "add an agent"
  - "create a workflow"
  - "DSPy signature"
  - "test code"
  - "memory operations"
  - "code analysis"
  - "pattern extraction"
capabilities:
  - Context-aware block loading (keyword-based)
  - Dual database search (NeonDB structured + ChromaDB semantic)
  - Pattern extraction with detailed code examples
  - Basic code analysis (DSPy signatures, agents, workflows, tools)
  - Session tracking in NeonDB
  - Auto-learning enabled
---

# Fleet Agent

A context-aware development assistant for AgenticFleet that maintains persistent memory across sessions using a hybrid NeonDB + ChromaDB architecture.

## Memory Architecture

### Dual Storage

- **ChromaDB (Semantic)**: Skills, patterns, code snippets with embedding-based search
- **NeonDB (Structured)**: Sessions, users, analytics, skill metadata with SQL queries

### Context Layers

1. **Core Memory** (`.fleet/context/core/`): Always loaded
   - `project.md`: Architecture, conventions, tech stack
   - `human.md`: User preferences, communication style
   - `persona.md`: Agent guidelines, tone

2. **Topic Blocks** (`.fleet/context/blocks/`): Loaded on demand
   - `project/`: commands, conventions, gotchas, architecture
   - `workflows/`: git, review
   - `decisions/`: ADRs

3. **Skills** (ChromaDB + NeonDB): Semantic + structured patterns

## Usage Examples

### Learn a Pattern

```
/fleet-agent learn --name "add_dspy_agent" --category "agent" --content "Create agent via AgentFactory with DSPyEnhancedAgent wrapper..."
```

### Recall Information

```
/fleet-agent recall "DSPy typed signatures"
/fleet-agent context "add a new agent for web search"
```

### Analyze Code

```
/fleet-agent analyze src/agents/coordinator.py
```

### Session Management

```
/fleet-agent session start
/fleet-agent session status
/fleet-agent session summary "Completed agent creation workflow"
```

## Commands

| Command                                                 | Description                    |
| ------------------------------------------------------- | ------------------------------ |
| `learn --name <name> --category <cat> --content <code>` | Save pattern to both databases |
| `recall <query>`                                        | Search NeonDB + ChromaDB       |
| `context <task>`                                        | Load relevant context blocks   |
| `analyze <file>`                                        | Analyze code structure         |
| `session start`                                         | Start new session              |
| `session status`                                        | Show current session           |
| `session summary <text>`                                | Save session summary           |
| `stats`                                                 | Show development metrics       |

## Auto-Learning

Automatically extracts and saves patterns after successful task completion with detailed code examples:

```yaml
name: pattern_add_dspy_signature
category: dspy
description: How to create a DSPy signature with TypedPredictor
implementation: |
  class TaskAnalysisOutput(BaseModel):
      complexity: Literal["low", "medium", "high"]

  class TaskAnalysis(dspy.Signature):
      task: str = dspy.InputField(desc="Task to analyze")
      analysis: TaskAnalysisOutput = dspy.OutputField()
```

## Implementation

Main script: `.fleet/context/scripts/fleet_agent.py`

Invocation: `uv run python .fleet/context/scripts/fleet_agent.py <command>`

Dependencies: `neon_memory.py`, `chroma_driver.py`, `memory_loader.py`

## See Also

- `memory-system-guide.md`: Complete memory system documentation
- `.fleet/context/MEMORY.md`: Memory hierarchy and commands
