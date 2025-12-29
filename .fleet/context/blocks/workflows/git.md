---
label: workflows-git
description: Git branching strategy, commit conventions, and collaboration workflow.
limit: 3000
scope: workflows
updated: 2024-12-29
---

# Git Workflow

## Branching Strategy

```
main
├── feature/new-feature
├── fix/bug-description
├── refactor/module-name
└── docs/update-readme
```

## Daily Workflow

### Starting Work
```bash
# Ensure main is up to date
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/my-feature
```

### During Development
```bash
# Stage and commit frequently
git add -p                    # Interactive staging
git commit -m "feat: description"

# Push to remote
git push -u origin feature/my-feature
```

### Before PR
```bash
# Rebase on latest main
git fetch origin
git rebase origin/main

# Run checks
make check
make test
```

## Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

### Types
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code refactoring
- `test` - Adding tests
- `chore` - Maintenance

### Examples
```
feat(api): add streaming endpoint for chat
fix(workflow): resolve race condition in routing
docs(readme): update installation instructions
refactor(dspy): simplify reasoner module
test(services): add chat service unit tests
```

## Safety Rules

- Never force push to `main`
- Never commit secrets or `.env` files
- Always run tests before pushing
- Use PR reviews for significant changes
