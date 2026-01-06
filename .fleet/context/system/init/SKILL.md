---
name: system-init
description: Comprehensive guide for initializing agent memory and project context. Use when setting up a new project, learning a codebase, or reorganizing memory blocks for project conventions, preferences, and workflows.
---

# System Initialization

This skill handles both the **technical setup** of the memory system and the **cognitive initialization** of understanding a project. It ensures directory structures, configuration files, and core context are in place, while also guiding systematic codebase exploration.

## When to Use This Skill

- **Fresh project**: Starting work on a new codebase
- **Existing project**: User wants to reorganize or update understanding
- **Deep dive**: User wants comprehensive analysis of the project
- **System repair**: Memory system structure needs reset

## Part 1: Technical Setup

### Quick Start

```bash
# 1. Initialize local files
uv run python .fleet/context/scripts/memory_manager.py init

# 2. Configure databases (edit config files with your credentials)
# .fleet/context/.chroma/config.yaml
# .fleet/context/.neon/config.yaml

# 3. Setup cloud collections
uv run python .fleet/context/scripts/memory_manager.py setup-chroma

# 4. Verify status
uv run python .fleet/context/scripts/memory_manager.py status
```

### Actions Performed

1. **Hydrates Templates**: Copies `core/*.template.md` to active `core/*.md` files if they don't exist
2. **Config Setup**: Ensures `.chroma/config.yaml` and `.neon/config.yaml` exist
3. **Recall Scratchpad**: Creates `recall/current.md` for session context

### Database Configuration

**ChromaDB Cloud** (`.fleet/context/.chroma/config.yaml`):

```yaml
cloud:
  api_key: "your-api-key"
  tenant: "your-tenant"
  database: "your-database"
  host: "api.trychroma.com"

collections:
  semantic: "agentic-fleet-semantic"
  procedural: "agentic-fleet-procedural"
  episodic: "agentic-fleet-episodic"
```

**NeonDB** (`.fleet/context/.neon/config.yaml`):

```yaml
cloud:
  host: "your-host.neon.tech"
  database: "neondb"
  user: "neondb_owner"
  password: "your-password"
```

### Collections Created

| Collection   | Name                     | Purpose                      |
| ------------ | ------------------------ | ---------------------------- |
| `semantic`   | agentic-fleet-semantic   | Facts about project and user |
| `procedural` | agentic-fleet-procedural | Learned skills and patterns  |
| `episodic`   | agentic-fleet-episodic   | Session history and context  |

## Part 2: Cognitive Initialization

After technical setup, systematically explore and document the codebase to build effective working memory.

### What to Remember About a Project

#### 1. Procedures (Rules & Workflows)

Explicit rules that should always be followed:

- "Never commit directly to main - always use feature branches"
- "Always run `make check` before committing"
- "Use conventional commits format"
- "Clear DSPy cache after modifying signatures"

#### 2. Preferences (Style & Conventions)

Project and user coding style preferences:

- "Use `type | None` not `Optional[type]`"
- "Absolute imports: `from agentic_fleet.utils import ...`"
- "Ruff formatter with line length 100"
- "Pydantic models for all DSPy outputs"

#### 3. History & Context

Important historical context that informs decisions:

- "DSPy compilation is offline-only as of v0.6.9"
- "Fast-path is disabled on follow-up turns intentionally"
- "The routing cache was added to reduce LLM calls"

### Memory Scope Considerations

**Project-scoped** (store in `core/project.md`, `blocks/`):

- Build commands, test commands, lint configuration
- Project architecture and key directories
- Team conventions specific to this codebase

**User-scoped** (store in `core/human.md`):

- Personal coding preferences
- Communication style preferences
- Current focus and active tasks

**Session-scoped** (store in `recall/current.md`):

- Current branch or ticket being worked on
- Debugging context for ongoing investigation
- Temporary notes about a specific task

### Research Depth Options

Ask the user which depth they prefer:

**Standard initialization** (~5-20 tool calls):

- Scan README, AGENTS.md, pyproject.toml, workflow_config.yaml
- Review git status and recent commits
- Explore key directories and understand project structure
- Update core memory blocks with essential information

**Deep research initialization** (~100+ tool calls):

- Everything in standard, plus:
- Use TodoWrite to create systematic research plan
- Deep dive into git history for patterns and context
- Analyze commit message conventions and branching strategy
- Explore multiple directories and understand architecture
- Search for and read key source files to understand patterns

### Research Techniques

**File-based research:**

- `AGENTS.md`, `README.md`, `CONTRIBUTING.md`
- `pyproject.toml`, `workflow_config.yaml`
- Config files (`.ruff.toml`, `.pre-commit-config.yaml`)
- CI/CD configs (`.github/workflows/`)

**Git-based research** (if in a git repo):

```bash
git log --oneline -20                    # Recent commits
git branch -a                            # Branching strategy
git log --format="%s" -50 | head -20     # Commit conventions
git shortlog -sn --all | head -10        # Main contributors
git diff main...HEAD                     # Current branch changes
```

**Codebase exploration:**

```bash
# Key directories for AgenticFleet
src/agentic_fleet/workflows/supervisor.py    # Main orchestration
src/agentic_fleet/agents/coordinator.py      # Agent creation
src/agentic_fleet/dspy_modules/reasoner.py   # DSPy module manager
src/agentic_fleet/config/workflow_config.yaml # All runtime settings
```

### Recommended Questions to Ask

Bundle these questions when starting:

1. **Research depth**: "Standard or deep research?"
2. **Identity**: "Which contributor are you?" (often inferrable from git)
3. **Communication style**: "Terse or detailed responses?"
4. **Specific rules**: "Any rules I should always follow?"

**What NOT to ask:**

- Things you can find by reading files
- Permission for obvious actions - just do them
- Questions one at a time - bundle them

## Your Task Checklist

1. [ ] **Run technical setup**: `memory_manager.py init` + `setup-chroma`
2. [ ] **Ask upfront questions**: Bundle the recommended questions
3. [ ] **Inspect existing context**: Read AGENTS.md, README, pyproject.toml
4. [ ] **Identify the user**: From git logs and their answers
5. [ ] **Research the project**: Based on chosen depth
6. [ ] **Update memory blocks**:
   - `core/project.md` - Architecture and conventions
   - `core/human.md` - User preferences and current focus
   - `blocks/project/gotchas.md` - Common pitfalls
7. [ ] **Reflect and review**: Check for completeness and quality
8. [ ] **Summarize**: Tell user what you learned and ask if done

## Reflection Phase

Before finishing, do a reflection step:

1. **Completeness check**: Did you gather all relevant information?
2. **Quality check**: Are there gaps or unclear areas?
3. **Structure check**: Would this information make sense to your future self?

**After reflection**, summarize:

> "I've completed the initialization. Here's a summary of what I set up: [summary]. Should I continue refining, or is this good to proceed?"

## Environment Variables (Optional)

Instead of config files, you can use environment variables:

- `CHROMA_API_KEY` - ChromaDB API key
- `CHROMA_TENANT` - ChromaDB tenant name
- `CHROMA_DATABASE` - ChromaDB database name
- `NEON_HOST` - NeonDB host
- `NEON_PASSWORD` - NeonDB password

## See Also

- `.fleet/context/MEMORY.md` - Complete memory system documentation
- `.fleet/context/SKILL.md` - Quick reference guide
- `.fleet/context/system/learn/SKILL.md` - How to learn new skills
- `.fleet/context/system/recall/SKILL.md` - How to search memory
- `.fleet/context/system/reflect/SKILL.md` - How to consolidate sessions
