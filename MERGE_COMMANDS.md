# Quick Merge Commands Reference

## Prerequisites
- Ensure you have merge permissions on the repository
- Install GitHub CLI: `gh` (https://cli.github.com/)
- Authenticate: `gh auth login`

## Command Templates

### Merge a PR (Squash)
```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

### Check PR Status
```bash
gh pr view <PR_NUMBER>
```

### List All Open PRs
```bash
gh pr list --state open
```

## Specific Merge Commands

### ⚠️ STEP 0: Fix PR #294 Conflicts FIRST
```bash
# Checkout the branch with conflicts
git checkout feature/magentic-models-utils
git fetch origin

# Rebase against main (includes #291 + #292)
git rebase origin/main

# Resolve conflicts manually in your editor
# After resolving, continue:
git add .
git rebase --continue

# Force push (with lease for safety)
git push --force-with-lease

# Verify CI passes, then merge via GitHub UI or:
gh pr merge 294 --squash --delete-branch
```

### STEP 1: Merge PR #293 (API/Responses)
```bash
# Check status
gh pr view 293

# Merge
gh pr merge 293 --squash --delete-branch

# Validate
make test-config
make check
uv run pytest tests/test_api_responses.py tests/test_api_entities.py
```

### STEP 2: Merge PR #295 (Workflows)
```bash
# Check status
gh pr view 295

# Merge
gh pr merge 295 --squash --delete-branch

# Validate
make test-config
make check
uv run pytest tests/test_workflow.py tests/test_workflow_factory.py
```

### STEP 3: Merge PR #296 (Frontend)
```bash
# Check status
gh pr view 296

# Merge
gh pr merge 296 --squash --delete-branch

# Validate
cd src/frontend && npm test && npm run lint
cd ../..
make dev  # Test full stack
```

### STEP 4: Merge PR #297 (Testing) - Independent
```bash
# Can merge any time after #291-#296
gh pr view 297
gh pr merge 297 --squash --delete-branch

# Validate
uv run pytest -v
cd tests/load_testing && make smoke
```

### STEP 5: Merge PR #298 (Config/Docs) - Final
```bash
# Can merge any time, recommended last
gh pr view 298
gh pr merge 298 --squash --delete-branch

# Validate
make check
```

## Post-Merge Validation Script

Create and run this after each merge:

```bash
#!/bin/bash
# post-merge-validate.sh

echo "🔍 Validating merge..."

echo "1️⃣ Configuration validation..."
make test-config || exit 1

echo "2️⃣ Code quality checks..."
make check || exit 1

echo "3️⃣ Running tests..."
uv run pytest -v || exit 1

echo "4️⃣ Workflow factory check..."
uv run python -c "from agenticfleet.api.workflow_factory import WorkflowFactory; factory = WorkflowFactory(); print(f'✓ Loaded {len(factory.list_available_workflows())} workflows')" || exit 1

echo "✅ All validations passed!"
```

Make it executable and use:
```bash
chmod +x post-merge-validate.sh
./post-merge-validate.sh
```

## CI Monitoring

After each merge, wait 2-3 minutes and check CI status:

```bash
# View recent workflow runs
gh run list --limit 5

# View specific workflow run
gh run view <RUN_ID>

# Watch workflow in real-time
gh run watch <RUN_ID>
```

## If CI Fails on Main

Create hotfix commit immediately:

```bash
# On main branch
git checkout main
git pull

# Make your fixes
# ... edit files ...

# Commit and push
git add .
git commit -m "hotfix: Fix CI failure after PR #XXX merge"
git push origin main

# Monitor CI
gh run watch
```

## Final Verification

After all 8 PRs are merged:

```bash
# 1. Pull latest main
git checkout main
git pull origin main

# 2. Full validation
make test-config
make check
uv run pytest

# 3. Full stack test
make dev
# Visit http://localhost:5173
# Test workflow execution
# Ctrl+C to stop

# 4. Verify all features work
echo "✅ All 8 PRs successfully merged!"
```

## Troubleshooting

### If a PR shows conflicts after previous merges
```bash
# Update the PR branch
git checkout <branch-name>
git fetch origin
git rebase origin/main
# Resolve conflicts
git push --force-with-lease

# Wait for CI, then merge
gh pr merge <PR_NUMBER> --squash --delete-branch
```

### If CI fails on a PR
```bash
# View CI logs
gh pr checks <PR_NUMBER>

# Get detailed logs
gh run view <RUN_ID> --log

# Fix in the PR branch, push, wait for CI, then merge
```

### If merge button is disabled
Possible reasons:
- CI checks not passing → Wait or check logs
- Merge conflicts → Rebase the PR branch
- Required reviews not met → Get approvals
- Branch not up to date → Update PR branch

## Reference Links

- PR #291: https://github.com/Qredence/agentic-fleet/pull/291 ✅ Merged
- PR #292: https://github.com/Qredence/agentic-fleet/pull/292 ✅ Merged
- PR #293: https://github.com/Qredence/agentic-fleet/pull/293
- PR #294: https://github.com/Qredence/agentic-fleet/pull/294 ⚠️ Conflicts
- PR #295: https://github.com/Qredence/agentic-fleet/pull/295
- PR #296: https://github.com/Qredence/agentic-fleet/pull/296
- PR #297: https://github.com/Qredence/agentic-fleet/pull/297
- PR #298: https://github.com/Qredence/agentic-fleet/pull/298

## Timeline Estimate

- Fix PR #294 conflicts: 10-15 minutes
- Merge PR #293-298 (sequential): 5-10 minutes each
- Total time: 45-60 minutes (including CI waits)
