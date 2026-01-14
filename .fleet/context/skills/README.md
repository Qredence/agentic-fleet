# Learned Skills

This directory contains **procedural memory** "handbooks" created by agents via the `/learn` skill.

## How it Works

1.  **Creation**: Agent solves a problem -> creates `.fleet/context/skills/my-solution.md`.
2.  **Indexing**: Agent runs `uv run python .fleet/context/scripts/memory_manager.py learn --file .fleet/context/skills/my-solution.md`.
3.  **Storage**: The file stays here (local backup), the content goes to Chroma Cloud (searchable).

## Privacy

By default, files in this directory (except this README) are **ignored by git**.
If you want to share a specific skill with the team, force add it:

```bash
git add -f .fleet/context/skills/useful-guide.md
```
