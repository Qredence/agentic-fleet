---
label: project-gotchas
description: Footguns, common pitfalls, and things to watch out for. Learn from past mistakes.
limit: 4000
scope: project
updated: 2024-12-29
---

# Project Gotchas

## DSPy Issues

### Cache Invalidation

**Problem**: Changes to prompts/signatures not reflected in output.
**Solution**: Clear DSPy cache after changes:

```bash
make clear-cache
```

### Compilation Mode

**Problem**: Slow first request, compilation happening at runtime.
**Solution**: DSPy compilation should be offline-only. Set `dspy.require_compiled: true` in workflow_config.yaml.

### Routing Latency

**Problem**: Multi-agent routing adds significant latency.
**Solution**: Use `gpt-4o-mini` for routing decisions. Simple tasks bypass routing via `is_simple_task()`.

## Workflow Issues

### Fast-Path on Follow-ups

**Problem**: Follow-up messages lose multi-turn context.
**Reason**: Fast-path is intentionally disabled on follow-up turns.
**Solution**: This is expected behavior - don't try to "fix" it.

### Checkpoint Semantics

**Problem**: Checkpoint and message sent together.
**Solution**: `checkpoint_id` is resume-only. Never send start message AND checkpoint_id together.

## Frontend Issues

### Playwright Browsers

**Problem**: E2E tests fail with "browser not found".
**Solution**: Install browsers first:

```bash
npx playwright install chromium
```

### Dev Server Ports

**Problem**: Port already in use.
**Solution**: Backend uses :8000, frontend uses :5173. Check for orphan processes.

## Environment Issues

### Virtual Environment

**Problem**: Wrong Python version or missing deps.
**Solution**: Never activate venvs manually. Always use `uv run ...`.

### Conversations Persistence

**Problem**: Chat history lost between sessions.
**Solution**: Conversations persist to `.var/data/conversations.json`. Delete file to reset.

## Common Mistakes

1. **Don't commit `.var/`** - Contains logs, caches, compiled DSPy outputs
2. **Don't use `pip` directly** - Always use `uv`
3. **Don't skip type hints** - Required for public APIs
4. **Don't hardcode paths** - Use config or environment variables
