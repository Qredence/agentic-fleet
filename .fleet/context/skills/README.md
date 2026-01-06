# Learned Skills

This directory contains **procedural memory** "handbooks" created by agents via the `/learn` skill.

## Directory Structure

Skills are organized as subdirectories with a `SKILL.md` file:

```
.fleet/context/skills/
├── README.md              # This file
├── SKILL_TEMPLATE.md      # Template for new skills
├── repo-cleanup/
│   └── SKILL.md           # Repository cleanup procedures
├── dspy-agent-framework-integration/
│   └── SKILL.md           # DSPy + Agent Framework patterns
├── dspy-agent-framework-quick-ref/
│   └── SKILL.md           # Quick reference card
└── memory-system-guide/
    └── SKILL.md           # Memory system usage guide
```

## How it Works

1. **Creation**: Agent solves a problem → creates `.fleet/context/skills/{skill-name}/SKILL.md`.
2. **Indexing**: Agent runs:
   ```bash
   uv run python .fleet/context/scripts/neon_learn.py .fleet/context/skills/{skill-name}/SKILL.md
   ```
3. **Storage**: The file stays here (local backup), content goes to ChromaDB + NeonDB (searchable).

## Creating a New Skill

1. Create directory: `mkdir -p .fleet/context/skills/my-skill`
2. Copy template: `cp .fleet/context/skills/SKILL_TEMPLATE.md .fleet/context/skills/my-skill/SKILL.md`
3. Edit the skill file
4. Index to databases:
   ```bash
   uv run python .fleet/context/scripts/neon_learn.py .fleet/context/skills/my-skill/SKILL.md
   ```

## Adding Supporting Files

Skills can include references or scripts:

```
.fleet/context/skills/my-skill/
├── SKILL.md               # Main skill document
├── references/            # Supporting documentation
│   └── best-practices.md
└── scripts/               # Helper scripts
    └── analyzer.py
```

## Privacy

By default, files in this directory are **ignored by git**.
If you want to share a specific skill with the team, force add it:

```bash
git add -f .fleet/context/skills/useful-skill/SKILL.md
```
