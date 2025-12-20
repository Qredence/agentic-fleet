# Doc Audit and Workflow

## Table of Contents

1. Purpose
2. Quick Start Checklist
3. Codebase Discovery
4. Doc Inventory and Audit Rubric
5. Plan Triggers (TODO vs ExecPlan)
6. Drafting and Refactoring Steps
7. AGENTS.md and Agent-First Docs Review
8. Validation Checklist

## 1. Purpose

Use this workflow to produce documentation that is accurate, current, and aligned with how the system actually runs. Treat code and configuration as the source of truth.

## 2. Quick Start Checklist

- Identify doc targets (README, AGENTS.md, docs/, architecture, runbooks).
- Find entry points, configs, and workflows (Makefile, scripts/, workflow config).
- Audit existing docs for drift and gaps.
- Decide: quick fixes vs. refactor plan.
- Draft updates with clear structure and diagrams as needed.
- Validate commands and links; update AGENTS.md if workflows changed.

## 3. Codebase Discovery

From repo root:

```bash
# from repo root
rg --files -g 'README*' -g 'AGENTS.md' -g 'docs/**' -g '*.md'
rg -n "(Makefile|pyproject|package\.json|workflow_config\.ya?ml|\.env\.example|docker|compose)" -g '*'
rg -n "(entrypoint|cli|main\(|app\.|FastAPI|Typer|Click)" src
```

Collect:

- Primary entry points and CLIs.
- Config files and runtime directories.
- How to run, test, lint, and develop.
- Architecture boundaries and main services/workflows.

## 4. Doc Inventory and Audit Rubric

Create a doc inventory with purpose + owner/area:

```
README.md: project overview, quick start
AGENTS.md: agent workflows and local conventions
/docs/architecture.md: system design
...
```

Audit each doc using this rubric:

- Accuracy: matches current code/config.
- Completeness: key flows and setup covered.
- Clarity: minimal jargon, clear steps.
- Usability: runnable commands, copy/paste ready.
- Maintainability: clear structure, changelog or decision log where needed.

Label issues by severity:

- Critical: incorrect commands, wrong architecture, broken setup.
- Major: missing core workflow or key prerequisite.
- Minor: formatting, minor clarity, outdated examples.

## 5. Plan Triggers (TODO vs ExecPlan)

Use a short TODO list for small edits in 1-2 files. Use an ExecPlan when:

- Reworking doc structure across multiple files.
- Introducing new architecture or workflow documentation.
- Large rewrites that affect onboarding or operations.

## 6. Drafting and Refactoring Steps

- Preserve existing conventions; do not invent new workflow names.
- Prefer short sections with clear headings.
- Keep steps atomic and ordered.
- Add "Source of Truth" notes when behavior depends on config.
- Add diagrams only where they reduce complexity.

## 7. AGENTS.md and Agent-First Docs Review

Check:

- Toolchain and commands match current repo state.
- Required environment variables and setup are accurate.
- Agent workflows, roles, and orchestration details are current.
- Any new conventions discovered during analysis are recorded.

If AGENTS.md is missing or stale, propose a fix and update it when approved.

## 8. Validation Checklist

- Commands run or are consistent with Makefile/scripts.
- Paths and filenames exist.
- Diagrams render (Mermaid syntax valid).
- Doc links resolve.
- AGENTS.md updated if workflows changed.
