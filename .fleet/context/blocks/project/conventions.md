---
label: project-conventions
description: Code style, commit format, PR process, and development standards.
limit: 4000
scope: project
updated: 2024-12-29
---

# Project Conventions

## Code Style

### Python
- **Formatter**: Ruff
- **Line length**: 100 characters
- **Python version**: 3.12+ syntax
- **Type hints**: Required for all public APIs
- **Docstrings**: Required for public functions/classes

### TypeScript/React
- **Formatter**: Prettier
- **Framework**: React 19 + Vite
- **Styling**: Tailwind CSS

## Git Conventions

### Commit Messages
Follow conventional commits:
```
type(scope): description

feat(api): add new chat endpoint
fix(workflow): resolve routing race condition
docs(readme): update installation steps
refactor(dspy): simplify reasoner logic
test(api): add chat service tests
```

### Branch Naming
```
feature/description
fix/description
refactor/description
docs/description
```

### Pull Requests
- Use PR template (`.github/pull_request_template.md`)
- Require passing CI checks
- Link related issues

## File Organization

### New Endpoints
1. Add route in `api/routes/`
2. Add service logic in `services/`
3. Add tests in `tests/api/`

### New Agents
1. Add agent in `agents/`
2. Update `workflow_config.yaml`
3. Add tests in `tests/agents/`

## Environment

### Required Variables
- `OPENAI_API_KEY` - Required for LLM calls
- `TAVILY_API_KEY` - Optional for web search

### Optional Variables
- `DSPY_COMPILE` - Enable DSPy compilation
- `LOG_JSON` - JSON logging (default: true)
