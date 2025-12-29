---
label: decisions-001-memory-system
description: ADR for the AgenticFleet memory system architecture decision.
limit: 4000
scope: decisions
updated: 2024-12-29
---

# ADR-001: Memory System Architecture

## Status

Accepted

## Context

AgenticFleet needed a persistent memory system for agents to:

- Learn from past interactions
- Store reusable skills and patterns
- Maintain context across sessions
- Enable semantic search over knowledge

## Decision

Implement a **Two-Tier Memory System**:

### Tier 1: Local Context (File-based)

```
.fleet/context/
├── core/           # Always in-context (project, human, persona)
├── blocks/         # Topic-scoped blocks (commands, architecture)
├── skills/         # Learned patterns and solutions
└── system/         # Agent skill definitions
```

### Tier 2: Chroma Cloud (Semantic Search)

- Collections: `semantic`, `procedural`, `episodic`
- Enables fuzzy/semantic search over all indexed content
- Private to user (Chroma Cloud credentials)

### Integration

- Symlinks in `.claude/skills/` for Claude Code discovery
- Scripts in `.fleet/context/scripts/` for CLI operations
- Memory blocks follow Letta-style format (label, description, limit)

## Alternatives Considered

### Alternative 1: Letta Cloud

- **Pro**: Full-featured memory API
- **Con**: External dependency, cost
- **Decision**: Use concepts, not platform

### Alternative 2: Local-only (no vector DB)

- **Pro**: Simpler setup
- **Con**: No semantic search capability
- **Decision**: Chroma Cloud provides semantic search with low complexity

### Alternative 3: MCP Server

- **Pro**: Universal tool integration
- **Con**: More complex, requires running server
- **Decision**: Deferred - use symlinks for now, MCP later

## Consequences

### Positive

- Agents can learn and improve over time
- Skills are shareable and git-managed
- Semantic search enables fuzzy retrieval
- Compatible with multiple AI tools (Claude Code, OpenCode)

### Negative

- Requires Chroma Cloud account setup
- Two-tier adds some complexity
- Symlinks may not work on all platforms

## References

- [Letta Memory Docs](https://docs.letta.com/guides/agents/memory/)
- [Chroma Agentic Memory](https://docs.trychroma.com/guides/build/agentic-memory)
- [Skill Learning Blog](https://www.letta.com/blog/skill-learning)
