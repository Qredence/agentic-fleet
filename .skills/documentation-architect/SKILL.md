---
name: documentation-architect
description: Create, review, and refactor project documentation (README, AGENTS.md, architecture docs, runbooks, API docs) with deep codebase analysis, clear markdown structure, and diagrams/user flows. Use when asked to write or improve docs, audit existing documentation for accuracy or quality, generate diagrams/flows, or assess agent-first docs like AGENTS.md/PLANS.md for freshness and completeness.
---

# Documentation Architect

## Overview

Produce high-quality, accurate documentation grounded in the actual codebase and current workflows. Deliver concise markdown, clear diagrams, and actionable doc audits or refactor plans.

## Workflow (use for most requests)

1. Clarify scope and audience (user, developer, operator, contributor).
2. Discover the codebase and existing docs; establish the source of truth.
3. Audit documentation for accuracy, gaps, and drift.
4. Decide on an update approach: quick edits vs. doc refactor plan.
5. Draft or refactor docs using the templates and structure guidance.
6. Add diagrams and user flows where they improve comprehension.
7. Verify commands, links, and examples; update AGENTS.md when workflows change.

Use the detailed workflow, audit rubric, and checklists in:

- `references/doc-audit-and-workflow.md`

Use markdown and doc templates in:

- `references/markdown-templates.md`

Use diagram and user-flow templates in:

- `references/diagram-templates.md`

## Decision Gates

Use these gates to choose outputs and effort:

- Docs exist and are mostly accurate: deliver a concise audit + targeted fixes.
- Docs exist but are stale or inconsistent: propose a refactor plan, then update docs.
- Docs missing: produce a documentation plan and draft core docs first.
- Large, multi-file changes: create or update an ExecPlan in `PLANS.md`.

## Output Expectations

Provide one or more of:

- Doc audit report with severity and concrete fixes.
- Updated markdown files with clear structure and consistent style.
- Diagrams/user flows embedded in docs (Mermaid by default).
- A plan (TODO list or ExecPlan) when refactors are large.

## Repo-First Alignment

Follow existing repo conventions (formatting, headings, diagram style, tooling). If no conventions exist, apply the templates and keep changes minimal.

## Resources

### references/

Load these as needed:

- `references/doc-audit-and-workflow.md`
- `references/markdown-templates.md`
- `references/diagram-templates.md`
