# AgenticFleet Memory System

This directory contains the **Agentic Memory System** for this project. It is designed to help agents learn, remember, and improve over time while keeping your private data safe.

## Architecture

The system uses a **Two-Tier Memory** architecture:

1.  **Local Context (Tier 1)**: File-based, git-tracked templates but local content.
    - `core/`: Identity, project architecture, and user preferences.
    - `blocks/`: Topic-scoped reference material (project, workflows, decisions).
    - `skills/`: Learned patterns and reusable solutions.
    - `recall/`: Session history and scratchpads.
    - `system/`: Agent skill definitions (commands).

2.  **Cloud Storage (Tier 2)**: Private semantic and structured search.
    - **ChromaDB Cloud**: Vector embeddings for semantic search.
      - `semantic`: Facts about the project and user.
      - `procedural`: Embeddings of learned skills.
      - `episodic`: History of past sessions.
    - **NeonDB**: Structured PostgreSQL storage.
      - Sessions, users, skill metadata with SQL queries.
      - Usage tracking and success rates.

## Directory Structure

```
.fleet/context/
├── MEMORY.md              # This file
├── SKILL.md               # Quick reference guide
├── core/                  # Core memory (always in-context)
│   ├── project.md         # Architecture, tech stack, conventions
│   ├── human.md           # User preferences, current focus
│   └── persona.md         # Agent guidelines, tone
├── blocks/                # Topic-scoped blocks (on-demand)
│   ├── project/           # commands, conventions, gotchas, architecture
│   ├── workflows/         # git, review
│   └── decisions/         # ADR-style decision records
├── skills/                # Learned skills (indexed to ChromaDB)
│   ├── README.md
│   ├── SKILL_TEMPLATE.md
│   └── *.md               # Individual skills
├── recall/                # Session context
│   ├── current.md         # Current session scratchpad
│   └── history.md         # Session archive
├── system/                # Agent skill definitions
│   ├── init/SKILL.md      # Initialize memory system
│   ├── learn/SKILL.md     # Learn new skills
│   ├── recall/SKILL.md    # Search memory
│   ├── reflect/SKILL.md   # Consolidate session learnings
│   └── fleet-agent/SKILL.md # Full-featured development assistant
├── scripts/               # Python memory engine
│   ├── memory_manager.py  # ChromaDB operations
│   ├── neon_memory.py     # NeonDB operations
│   ├── neon_learn.py      # Dual-database learning
│   ├── fleet_agent.py     # Fleet agent implementation
│   └── *.py               # Supporting scripts
├── .chroma/               # ChromaDB Cloud config
│   └── config.yaml
└── .neon/                 # NeonDB config
    └── config.yaml
```

## Setup (First Run)

1.  **Install Dependencies**:

    ```bash
    uv pip install chromadb psycopg2-binary openai pyyaml
    ```

2.  **Configure Databases**:

    Copy templates and add your credentials:

    ```bash
    # ChromaDB
    cp .fleet/context/.chroma/config.template.yaml .fleet/context/.chroma/config.yaml

    # NeonDB
    cp .fleet/context/.neon/config.template.yaml .fleet/context/.neon/config.yaml
    ```

3.  **Initialize Memory**:

    ```bash
    uv run python .fleet/context/scripts/memory_manager.py init
    uv run python .fleet/context/scripts/memory_manager.py setup-chroma
    ```

4.  **Verify Status**:

    ```bash
    uv run python .fleet/context/scripts/memory_manager.py status
    ```

## System Commands

The `system/` directory contains skill definitions that agents can invoke:

| Command    | Script/Skill                  | Description                                           |
| ---------- | ----------------------------- | ----------------------------------------------------- |
| `/init`    | `system/init/SKILL.md`        | Initialize memory system, hydrate templates           |
| `/learn`   | `system/learn/SKILL.md`       | Index a skill file to ChromaDB + NeonDB               |
| `/recall`  | `system/recall/SKILL.md`      | Semantic search across all memory collections         |
| `/reflect` | `system/reflect/SKILL.md`     | Consolidate session, archive to history               |
| `/fleet`   | `system/fleet-agent/SKILL.md` | Full development assistant with context-aware loading |

### Command Details

#### `/init` - Initialize Memory System

Hydrates templates, creates config files, sets up recall scratchpad.

```bash
uv run python .fleet/context/scripts/memory_manager.py init
uv run python .fleet/context/scripts/memory_manager.py setup-chroma
```

#### `/learn` - Learn a Skill

Indexes a markdown file to both ChromaDB (semantic) and NeonDB (structured).

```bash
# Using memory_manager (ChromaDB only)
uv run python .fleet/context/scripts/memory_manager.py learn --file .fleet/context/skills/my-skill.md

# Using neon_learn (ChromaDB + NeonDB)
uv run python .fleet/context/scripts/neon_learn.py .fleet/context/skills/my-skill.md
```

#### `/recall` - Search Memory

Semantic search across all memory collections.

```bash
uv run python .fleet/context/scripts/memory_manager.py recall "your query"
```

#### `/reflect` - Consolidate Session

Archives the current session context and indexes to episodic memory.

**Workflow**:

1. Read `.fleet/context/recall/current.md` to see session context
2. Summarize: tasks completed, decisions made, open issues
3. Append summary to `.fleet/context/recall/history.md`
4. Reset `current.md` for the next session
5. Optionally index to ChromaDB episodic collection

```bash
uv run python .fleet/context/scripts/memory_manager.py reflect
```

#### `/fleet` - Fleet Agent

Full-featured development assistant with dual-database operations.

```bash
uv run python .fleet/context/scripts/fleet_agent.py recall "DSPy typed signatures"
uv run python .fleet/context/scripts/fleet_agent.py context "add a new agent"
uv run python .fleet/context/scripts/fleet_agent.py session start
```

## Usage

### For Agents

Agents are instructed to use this system via `AGENTS.md`.

- **Start**: Read `core/project.md` and `core/human.md`.
- **Search**: Use `/recall "query"` to find relevant skills or past solutions.
- **Learn**: Use `/learn` after solving a difficult problem to document the solution.
- **Reflect**: Use `/reflect` at the end of a session to consolidate learnings.

### For Humans

You can manually edit any file in `core/`, `blocks/`, or `skills/`.

- **`core/project.md`**: Update this when architecture changes.
- **`core/human.md`**: Update this with your preferences and current focus.
- **`blocks/project/gotchas.md`**: Add common pitfalls as you encounter them.
- **`skills/*.md`**: Write new guides manually using `SKILL_TEMPLATE.md`.

## Privacy & Git

- **Public Safe**: The _structure_ (scripts, templates, system definitions) is committed to Git.
- **Private Safe**: Your _content_ (actual `.md` files in core/skills, and config with credentials) is ignored via `.gitignore`.

### Gitignored Files

```
.fleet/context/.chroma/config.yaml    # Contains API keys
.fleet/context/.neon/config.yaml      # Contains passwords
.fleet/context/core/human.md          # Personal preferences
.fleet/context/recall/*.md            # Session data
.fleet/context/skills/*.md            # Learned patterns (local only)
```

## Database Collections

### ChromaDB Collections

| Collection   | Name                     | Purpose                         |
| ------------ | ------------------------ | ------------------------------- |
| `semantic`   | agentic-fleet-semantic   | Facts about project and user    |
| `procedural` | agentic-fleet-procedural | Learned skills and patterns     |
| `episodic`   | agentic-fleet-episodic   | Session history and reflections |

### NeonDB Tables

| Table      | Purpose                            |
| ---------- | ---------------------------------- |
| `sessions` | Track agent sessions with metadata |
| `skills`   | Skill metadata with usage counts   |
| `users`    | User preferences and context       |
| `memories` | Structured memory entries          |

## See Also

- `SKILL.md` - Quick reference for the memory system
- `skills/memory-system-guide.md` - Detailed usage guide
- `system/fleet-agent/SKILL.md` - Full agent documentation
