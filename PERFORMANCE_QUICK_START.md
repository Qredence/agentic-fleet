# Performance Quick Start

> **TL;DR**: Comprehensive analysis complete. 247 complexity issues found. 1 critical concurrency bug. Zero duplicates. See detailed docs below.

## 🚀 Start Here

1. **Read Analysis**: [`PERFORMANCE_ANALYSIS.md`](./PERFORMANCE_ANALYSIS.md) - Full context and findings
2. **Implement Fixes**: [`PERFORMANCE_IMPROVEMENTS.md`](./PERFORMANCE_IMPROVEMENTS.md) - Code changes and plan
3. **Track Progress**: Use checklist below

## 🎯 Top 5 Issues to Fix

| # | Issue | File | Priority | Effort |
|---|-------|------|----------|--------|
| 1 | Concurrency bug | `src/agentic_fleet/api/middleware.py:186` | 🔴 Critical | 2-3h |
| 2 | WebSocket complexity | `src/agentic_fleet/services/chat_websocket.py:526` | 🔴 Critical | 4-6h |
| 3 | Event mapping length | `src/agentic_fleet/api/events/mapping.py:385` | 🟠 High | 6-8h |
| 4 | SSE complexity | `src/agentic_fleet/services/chat_sse.py:70` | 🟠 High | 2-3h |
| 5 | Agent shims | `src/agentic_fleet/utils/agent_framework_shims.py:79` | 🟢 FIXED | 2h |

## ✅ Implementation Checklist

### Week 1: Critical Fixes ✅ COMPLETED
- [x] Fix `BridgeMiddleware` concurrency with contextvars
- [x] Add concurrent request test (`test_middleware_concurrency.py`)
- [x] Validate with 10 concurrent connections
- [x] No data corruption or race conditions

### Week 2: Event Mapping
- [ ] Extract event handlers to separate functions
- [ ] Create dispatch table (`_EVENT_HANDLERS`)
- [ ] Test all 15+ event types
- [ ] Benchmark: event mapping time < 1ms

### Week 3: WebSocket Handler  
- [ ] Extract `_setup_session()` 
- [ ] Extract `_message_loop()`
- [ ] Extract `_handle_task_message()`
- [ ] Test WebSocket flows (connect, send, receive, disconnect)
- [ ] Complexity reduced from 76 to < 15

### Week 4: Polish ✅ COMPLETED (Partial)
- [x] Split agent shims into focused patchers
- [ ] Extract SSE `_setup_stream_context()`
- [ ] Run full test suite
- [ ] Final performance validation (p50/p99 latency)

## 🔧 Run Analysis Tools

```bash
# Complexity (247 issues found)
python3 .github/skills/python-backend-reviewer/scripts/complexity_analyzer.py src/agentic_fleet/

# Concurrency (1 real issue)
python3 .github/skills/python-backend-reviewer/scripts/concurrency_analyzer.py src/agentic_fleet/services/ src/agentic_fleet/api/

# Duplicates (✅ none found)
python3 .github/skills/python-backend-reviewer/scripts/detect_duplicates.py src/agentic_fleet/
```

## 📊 Expected Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| WebSocket complexity | 76 | Pending | Week 3 |
| Event mapping lines | 580 | Pending | Week 2 |
| SSE complexity | 37 | Pending | Week 4 |
| Concurrency bugs | 1 | 0 | ✅ 100% fixed |
| Agent shims complexity | 34 | ~5 | ✅ 85% reduction |
| Code duplicates | 0 | 0 | ✅ Maintained |

## 📖 Full Documentation

- **Analysis**: [`PERFORMANCE_ANALYSIS.md`](./PERFORMANCE_ANALYSIS.md) (424 lines)
- **Implementation**: [`PERFORMANCE_IMPROVEMENTS.md`](./PERFORMANCE_IMPROVEMENTS.md) (798 lines)
- **Summary**: [`docs/performance/README.md`](./docs/performance/README.md)

## 🤝 Need Help?

- **Understanding issues?** → Read `PERFORMANCE_ANALYSIS.md`
- **Implementing fixes?** → Follow `PERFORMANCE_IMPROVEMENTS.md`
- **Tool usage?** → Check `.github/skills/python-backend-reviewer/SKILL.md`

---

**Status**: ✅ Week 1 & Week 4 (Partial) Complete  
**Fixed**: Critical concurrency bug + Agent shims refactored  
**Next**: Week 2-3 (Event mapping, WebSocket) - Can continue in follow-up PRs  
**Timeline**: Remaining 2 weeks for full implementation
