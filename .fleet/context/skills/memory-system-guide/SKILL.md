---
title: AgenticFleet Memory System Guide
tags: [memory, documentation, setup]
author: AgenticFleet Architect
created: 2024-12-29
---

# AgenticFleet Memory System Guide

> **A comprehensive guide to using the Two-Tier Memory System (Local + Chroma Cloud) for persistent agent context.**

## Context

**When to use this skill:**

- You are a new agent or contributor starting a session.
- You need to recall past architectural decisions or debugging solutions.
- You want to save a new complex solution for the future.

**Prerequisites:**

- Python dependencies installed: `uv pip install -r .context/scripts/requirements.txt`
- Chroma Cloud configured in `.context/.chroma/config.yaml`.

## Step-by-Step Guide

### 1. Initialization

At the start of a session, always hydrate the local context.

```bash
uv run python .fleet/context/scripts/memory_manager.py init
```

### 2. Recalling Information (Semantic Search)

To find information stored in Chroma Cloud:

```bash
uv run python .fleet/context/scripts/memory_manager.py recall "how to fix cors error"
```

This queries the `semantic` (facts) and `procedural` (skills) collections.

### 3. Learning (Saving New Skills)

When you solve a tough problem:

1.  Create a markdown file in `.context/skills/` (e.g., `fix-auth-bug.md`).
2.  Use the `SKILL_TEMPLATE.md` structure.
3.  Index it into Chroma:
    ```bash
    uv run python .context/scripts/memory_manager.py learn --file .context/skills/fix-auth-bug.md
    ```

### 4. Reflection (End of Session)

Summarize your work to keep the history clean.

```bash
uv run python .fleet/context/scripts/memory_manager.py reflect
```

## Common Pitfalls

- **Not Configuring Chroma**: If `config.yaml` is missing or has no keys, the system falls back to local-only (no search).
- **Committing Private Data**: Never force-add files in `core/` or `skills/` unless they are generic templates.
- **Forgetting to Learn**: Solving a problem without running `/learn` means the next agent has to solve it again.

## Related Resources

- `AGENTS.md` (System Instructions)
- `.fleet/context/MEMORY.md` (Architecture Docs)
