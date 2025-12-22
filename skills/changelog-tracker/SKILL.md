---
name: changelog-tracker
description: Track and summarize repository changes into CHANGELOG.md with a clear, concise Unreleased section. Use when asked to draft or update changelog entries, summarize recent features/fixes, or maintain release notes. Derive the version from pyproject.toml and the date from today; combine git history (since last tag) with user-provided notes and categorize by backend/frontend/docs/tests/ci/infra.
---

# Changelog Tracker

## Overview

Create or update the **Unreleased** section in CHANGELOG.md by combining git history since the latest tag with user notes, then write concise, categorized bullets. Version comes from pyproject.toml and date is today.

## Quick start

From repo root:

```bash
# from repo root
python3 skills/changelog-tracker/scripts/collect_changes.py
```

If you need machine-readable output:

```bash
# from repo root
python3 skills/changelog-tracker/scripts/collect_changes.py --json
```

## Workflow

1. Inspect CHANGELOG.md

- Ensure there is an **Unreleased** section at the top.
- Preserve the existing format and heading style.

2. Gather inputs

- Run `collect_changes.py` to get:
  - latest tag (if any)
  - commit list since tag
  - files grouped by area
  - version from `pyproject.toml`
- Ask the user for any additional notes (backend/frontend/docs/etc).

3. Draft the Unreleased entry

- Summarize impact first, then internal changes.
- Use short bullets with clear verbs.
- Prefer these sections when relevant: Highlights, Backend, Frontend, Docs, Tests, CI/Infra, Security, Migration Notes.
- If no latest tag exists, note that the comparison scope is the full history or last commit range.

4. Update CHANGELOG.md

- Add or refresh the **Unreleased** section.
- Keep existing release entries intact.
- Include version/date if the file expects it, otherwise only change Unreleased content.

5. Confirm with the user

- Ask for approval before writing changes.

## Notes

- Use `references/changelog-format.md` for categorization and tone guidance.
- If the git history is noisy, prioritize commits touching user-facing paths and summarize the rest.

## Resources

### scripts/

- `collect_changes.py`: Gather commits and file-path buckets since the latest tag (or override).

### references/

- `changelog-format.md`: Local formatting and categorization guidance for AgenticFleet.
