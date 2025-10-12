# AgenticFleet Documentation

**Version:** 0.5.0  
**Last Updated:** October 12, 2025

Welcome! The docs are now arranged by intent so you can jump straight to what you need.

## Directory Map
- **getting-started/**
  - [`command-reference.md`](getting-started/command-reference.md) – uv + Makefile command catalogue.
  - [`quick-reference.md`](getting-started/quick-reference.md) – one-page onboarding checklist.
- **overview/**
  - [`implementation-summary.md`](overview/implementation-summary.md) – architecture deep dive + component guide.
  - [`progress-tracker.md`](overview/progress-tracker.md) – milestone status and roadmap.
- **operations/**
  - [`developer-environment.md`](operations/developer-environment.md) – uv workflow, tooling, CI guardrails.
  - [`github-actions-setup.md`](operations/github-actions-setup.md) – workflow catalogue and protection rules.
  - [`github-workflows-overview.md`](operations/github-workflows-overview.md) – plain-language description of each workflow.
  - [`mem0-integration.md`](operations/mem0-integration.md) – persistent memory configuration.
  - [`pypi-environment-setup.md`](operations/pypi-environment-setup.md) – trusted publishing + API token instructions.
  - [`repository-guidelines.md`](operations/repository-guidelines.md) – coding standards and review practices.
  - [`workflows-quick-reference.md`](operations/workflows-quick-reference.md) – job-by-job cheat sheet.
- **migrations/**
  - [`responses-api-migration.md`](migrations/responses-api-migration.md) – OpenAI Responses client migration notes.
  - [`src-layout-migration.md`](migrations/src-layout-migration.md) – summary of the 0.5.0 package restructure.
- **runbooks/**
  - [`troubleshooting.md`](runbooks/troubleshooting.md) – recurring issues (tag rules, ChatAgent params, mem0 regression tests).
- **releases/**
  - [`2025-10-12-v0.5.0.md`](releases/2025-10-12-v0.5.0.md) – release changelog and validation evidence.
- **archive/**
  - Historical clean-up checklists and .github remediation summaries retained for audit.

## Start Here
1. **New contributor?** Read [`../README.md`](../README.md) then skim the items in `getting-started/`.
2. **Maintaining pipelines?** Jump to `operations/`.
3. **Investigating regressions?** Check `runbooks/`.

## Contributing to Docs
- Keep new material inside one of the folders above; use kebab-case filenames.
- Update this index whenever you add, move, or retire a document.
- Prefer linking to sections rather than duplicating content across guides.

For feedback or questions, open an issue or email contact@qredence.ai.
