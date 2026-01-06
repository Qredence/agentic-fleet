---
name: system-learn
description: Ingest new procedural memory (skills, patterns, docs) into the dual-database storage (NeonDB + ChromaDB).
---

# Learning Skill

This skill allows the agent to "learn" new patterns, skills, or documentation by ingesting markdown files into both:

- **NeonDB**: Structured storage with usage tracking
- **ChromaDB**: Semantic embeddings for similarity search

## Directory Structure

Skills should be organized as subdirectories:

```
.fleet/context/skills/{skill-name}/
├── SKILL.md               # Main skill document (required)
├── references/            # Optional supporting docs
└── scripts/               # Optional helper scripts
```

## Usage

### Dual-Database Learning (Recommended)

Indexes to both NeonDB and ChromaDB:

```bash
uv run python .fleet/context/scripts/neon_learn.py .fleet/context/skills/{skill-name}/SKILL.md
```

### ChromaDB Only

For ChromaDB-only indexing:

```bash
uv run python .fleet/context/scripts/memory_manager.py learn --file .fleet/context/skills/{skill-name}/SKILL.md
```

## Creating a New Skill

1. **Create directory**:

   ```bash
   mkdir -p .fleet/context/skills/my-skill
   ```

2. **Create skill file**:

   ```bash
   cp .fleet/context/skills/SKILL_TEMPLATE.md .fleet/context/skills/my-skill/SKILL.md
   ```

3. **Edit the skill** with your content

4. **Index to databases**:
   ```bash
   uv run python .fleet/context/scripts/neon_learn.py .fleet/context/skills/my-skill/SKILL.md
   ```

## Skill File Format

Use the template with frontmatter:

```markdown
---
title: Descriptive Title
tags: [tag1, tag2]
author: Agent Name
created: YYYY-MM-DD
---

# Skill Title

## Context

When to use this skill...

## Solution

Step-by-step instructions...

## Pitfalls & Troubleshooting

Common issues...
```

## Best Practices

- Use descriptive directory names (kebab-case)
- Include frontmatter with title, tags, created date
- The file should contain **reusable** information, not ephemeral session data
- Add references/ subdirectory for supporting documentation
- Index after creation to make it searchable

## Example

```bash
# Create skill
mkdir -p .fleet/context/skills/dspy-typed-signatures
cp .fleet/context/skills/SKILL_TEMPLATE.md .fleet/context/skills/dspy-typed-signatures/SKILL.md

# Edit...

# Index
uv run python .fleet/context/scripts/neon_learn.py .fleet/context/skills/dspy-typed-signatures/SKILL.md
```

Output:

```
============================================================
LEARNING SKILL: dspy-typed-signatures
============================================================

[1/2] Saving to NeonDB...
  ✓ Saved to NeonDB: dspy-typed-signatures

[2/2] Indexing to ChromaDB...
  ✓ Indexed to ChromaDB: skill_dspy-typed-signatures

============================================================
SKILL LEARNED: dspy-typed-signatures
  Category: general
  NeonDB: tracking usage & success rate
  ChromaDB: semantic search enabled
============================================================
```
