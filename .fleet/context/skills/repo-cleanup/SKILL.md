---
title: Repository Cleanup and Git Hygiene
tags: [git, cleanup, maintenance, hygiene]
author: OpenCode
created: 2024-12-30
---

# Repository Cleanup and Git Hygiene

## Context

**When to use this skill:**

- Repository has accumulated unused directories from various AI tools
- Files are tracked despite being in `.gitignore` (committed before rule was added)
- GitHub Agentic Workflows logs are taking up disk space
- Need to clean up before a release

**Why this matters:**

- Keeps repository clean and professional
- Reduces disk usage from accumulated logs
- Prevents accidental commits of local-only files

## Solution

### Step 1: Identify Candidates for Removal

```bash
# Check what's in .gitignore but still present locally
git ls-files --others --ignored --exclude-standard | head -50

# Check which directories are gitignored
git check-ignore .data .factory .junie .kilocode .letta .skills .idea report/

# Find directories with sizes
du -sh */ .*/ 2>/dev/null | sort -hr | head -20
```

### Step 2: Untrack Files Already Committed

If files were committed before being added to `.gitignore`:

```bash
# Untrack but keep locally
git rm --cached -r <path>

# Example: untrack .skills/ directory
git rm --cached -r .skills/
```

This removes from git tracking but preserves local files.

### Step 3: Clean GitHub Agentic Workflows Logs

The `.github/aw/logs/` directory accumulates run logs. Best practice `.gitignore`:

```gitignore
# .github/aw/logs/.gitignore
*
!.gitignore
```

Clean up run directories:

```bash
# Check size
du -sh .github/aw/logs/

# Delete run directories (preserves .gitignore)
rm -rf .github/aw/logs/run-*
```

### Step 4: Delete Unused AI Tool Directories

Common AI tool directories that can be safely deleted:

```bash
# All are typically gitignored
rm -rf .junie/      # JetBrains AI
rm -rf .idea/       # JetBrains IDE settings
rm -rf .kilocode/   # Kilocode AI tool
rm -rf .factory/    # Factory AI tool
rm -rf .data/       # Legacy cache (use .var/ instead)
rm -rf report/      # Generated jscpd reports
```

**Check before deleting:**

- `.letta/` - May contain memory tool config
- `.factory/` - May contain skills you want to keep

### Verification

```bash
# Verify directories removed
ls -d .junie .idea .kilocode 2>&1  # Should show "No such file"

# Check git status
git status --short

# Check disk space recovered
du -sh .
```

## Pitfalls & Troubleshooting

**Problem**: `git rm --cached` shows files as "deleted" in status

- **Cause**: Normal - files are deleted from index, not disk
- **Fix**: This is expected. Commit the changes.

**Problem**: Can't delete directory - permission denied

- **Cause**: Process using the files
- **Fix**: Close IDEs and processes, try again

**Problem**: Accidentally deleted files you needed

- **Cause**: Files weren't backed up
- **Fix**: If in git history, use `git checkout HEAD -- <path>`

## Related Resources

- **Internal**:
  - `.fleet/context/blocks/project/gotchas.md` - Git hygiene section
  - `.gitignore` - Project ignore patterns

- **External**:
  - [GitHub Agentic Workflows](https://github.com/githubnext/gh-aw)

## Notes

- Always verify what you're deleting before running `rm -rf`
- Local-only directories (`.skills/`, `.factory/`) should stay gitignored
- Run this cleanup periodically, especially before releases

---

**Last Updated**: 2024-12-30
**Status**: Active
