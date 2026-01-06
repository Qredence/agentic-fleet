---
name: system-learn
description: Ingest new procedural memory (skills, patterns, docs) into the vector database.
---

# Learning Skill

This skill allows the agent to "learn" new patterns, skills, or documentation by ingesting markdown files into the `procedural` memory collection in ChromaDB.

## Usage

Use this when you have identified a reusable pattern, wrote a new guide, or want to index a documentation file for future semantic retrieval.

```bash
uv run python .fleet/context/scripts/memory_manager.py learn --file <path_to_markdown_file>
```

## Arguments

- `--file`: The absolute or relative path to the markdown file you want to learn.

## Best Practices

- Ensure the markdown file has a clear title (# Title).
- The file should contain reusable information, not just ephemeral session data.
- Save the file in `.fleet/context/skills/` before learning it to keep the source organized.
