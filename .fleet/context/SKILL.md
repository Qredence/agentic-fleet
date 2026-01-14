---
name: memory-system
description: Complete guide to the AgenticFleet memory system. Read this first.
---

# AgenticFleet Memory System

A two-tier memory architecture enabling agents to learn, remember, and improve over time.

## Quick Start

1. **Initialize** (first time only):

   ```bash
   uv run python .fleet/context/scripts/memory_manager.py init
   ```

2. **Setup Chroma Cloud** (after editing config with your API key):

   ```bash
   uv run python .fleet/context/scripts/memory_manager.py setup-chroma
   ```

3. **Verify Status**:

   ```bash
   uv run python .fleet/context/scripts/memory_manager.py status
   ```

4. **Read Core Context** (always do this first):
   - `.fleet/context/core/project.md` - Project architecture
   - `.fleet/context/core/human.md` - User preferences
   - `.fleet/context/core/persona.md` - Agent guidelines

5. **Search Memory** when you need information:

   ```bash
   uv run python .fleet/context/scripts/memory_manager.py recall "your query"
   ```

6. **Create Skills** after solving problems:
   ```bash
   uv run python .fleet/context/scripts/memory_manager.py learn --file .fleet/context/skills/new-skill.md
   ```

## Memory Hierarchy

### Core Memory (Always In-Context)

Location: `.fleet/context/core/`

| Block        | Purpose                               |
| ------------ | ------------------------------------- |
| `project.md` | Architecture, tech stack, conventions |
| `human.md`   | User preferences, communication style |
| `persona.md` | Agent role, tone, guidelines          |

### Topic Blocks (Reference On-Demand)

Location: `.fleet/context/blocks/`

| Category     | Blocks                                       |
| ------------ | -------------------------------------------- |
| `project/`   | commands, architecture, conventions, gotchas |
| `workflows/` | git, review                                  |
| `decisions/` | ADR-style decision records                   |

### Skills (Procedural Memory)

Location: `.fleet/context/skills/`

Learned patterns and solutions. Indexed to Chroma for semantic search.

### Chroma Cloud (Semantic Search)

Collections: `semantic`, `procedural`, `episodic`

Enables fuzzy search across all indexed content.

## Commands

### Claude Code Commands

```
/init              # Initialize memory system
/learn             # Learn a new skill
/recall            # Search memory semantically
/reflect           # Reflect on session, consolidate learnings
```

### CLI Commands

```bash
# Initialize system (creates local files)
uv run python .fleet/context/scripts/memory_manager.py init

# Setup Chroma Cloud collections
uv run python .fleet/context/scripts/memory_manager.py setup-chroma

# Check connection and collection status
uv run python .fleet/context/scripts/memory_manager.py status

# Semantic search across all collections
uv run python .fleet/context/scripts/memory_manager.py recall "query"

# Index skill to Chroma procedural collection
uv run python .fleet/context/scripts/memory_manager.py learn --file <path>

# Archive session to episodic collection
uv run python .fleet/context/scripts/memory_manager.py reflect
```

## Block Format

All memory blocks use Letta-style frontmatter:

```yaml
---
label: block-name
description: What this block contains and when to use it.
limit: 5000 # Character limit
scope: core|project|workflows|decisions
updated: 2024-12-29
---
# Content here...
```

## Workflow

### Starting a Session

1. Read core blocks (project, human, persona)
2. Check relevant topic blocks if needed
3. Use `/recall` to search for relevant skills

### During Work

1. Reference blocks as needed
2. Update `human.md` if you learn user preferences
3. Note patterns worth remembering

### Ending a Session

1. Use `/reflect` to consolidate learnings
2. Create skills for reusable solutions
3. Index new skills with `/learn`

## File Structure

```
.fleet/context/
├── SKILL.md                    # This file (entry point)
├── MEMORY.md                   # Detailed documentation
├── core/                       # Core memory blocks
├── blocks/                     # Topic-scoped blocks
│   ├── project/
│   ├── workflows/
│   └── decisions/
├── skills/                     # Learned skills
├── system/                     # Agent skill definitions
├── scripts/                    # Python memory engine
└── .chroma/                    # Chroma Cloud config
```

## Related Documentation

- `MEMORY.md` - Detailed setup and architecture
- `skills/README.md` - How to create skills
- `skills/SKILL_TEMPLATE.md` - Skill template
- `blocks/decisions/001-memory-system.md` - Architecture decision record
