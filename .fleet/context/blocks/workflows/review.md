---
label: workflows-review
description: PR review process, checklist, and quality gates.
limit: 3000
scope: workflows
updated: 2024-12-29
---

# Code Review Workflow

## Creating a PR

1. **Title**: Use conventional commit format
   ```
   feat(api): add new chat streaming endpoint
   ```

2. **Description**: Use PR template
   - Summary of changes
   - Related issues
   - Testing done
   - Screenshots (if UI)

3. **Labels**: Add appropriate labels
   - `feature`, `bug`, `docs`, `refactor`
   - `needs-review`, `wip`

## Review Checklist

### Code Quality
- [ ] Types are correct and complete
- [ ] No unnecessary complexity
- [ ] Functions are focused and testable
- [ ] Error handling is appropriate

### Testing
- [ ] Tests pass (`make test`)
- [ ] New code has tests
- [ ] Edge cases covered
- [ ] No flaky tests introduced

### Documentation
- [ ] Docstrings for public APIs
- [ ] README updated if needed
- [ ] CHANGELOG entry added

### Security
- [ ] No secrets in code
- [ ] Input validation present
- [ ] No SQL injection risks
- [ ] Dependencies are trusted

## Reviewer Guidelines

### Approval Criteria
- All CI checks pass
- At least one approval
- No unresolved comments
- No merge conflicts

### Feedback Style
- Be specific and constructive
- Suggest solutions, not just problems
- Use "nit:" prefix for minor suggestions
- Approve with minor suggestions if appropriate

## Merge Process

1. Squash and merge (default)
2. Delete branch after merge
3. Verify deployment if applicable
