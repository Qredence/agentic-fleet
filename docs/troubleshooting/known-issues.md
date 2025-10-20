# Known Issues & Limitations

Current limitations and known issues in AgenticFleet v0.5.3.

---

## Known Issues

### E2E Tests Require Running Server

**Issue:** End-to-end tests fail in CI when server isn't running.

**Status:** ✅ Fixed in v0.5.3

**Workaround:** E2E tests are now marked with `@pytest.mark.e2e` and excluded from CI via `-m "not e2e"`. Run manually with `uv run pytest -m e2e` when server is running.

**Related:** Tests in `tests/e2e/` and `tests/test_reflection_endpoint.py`

---

### Mock Web Search Only

**Issue:** Web search tool returns mock data by default, not real search results.

**Status:** ⚠️ Known limitation

**Impact:** Researcher agent responses are based on predefined mock data rather than live web searches.

**Workaround:**
- Use for development/testing
- Implement real search integration (see `agents/researcher/tools/web_search_tools.py`)
- Consider integrating:
  - Google Custom Search API
  - Bing Search API
  - Tavily API
  - SerpAPI

**Future:** Real search integration planned for future release.

---

### Windows Path Issues

**Issue:** Some path operations may fail on Windows due to path separator differences.

**Status:** ⚠️ Minor issue

**Impact:** Checkpointing and log file creation may have issues on Windows.

**Workaround:**
- Use WSL2 (Windows Subsystem for Linux) - recommended
- Or ensure paths use forward slashes in configuration

---

### Rate Limiting

**Issue:** OpenAI rate limits can cause workflow failures during high-round-count tasks.

**Status:** ⚠️ Expected behavior

**Impact:** Workflows may fail with `RateLimitError` when limits exceeded.

**Workaround:**
```yaml
# Reduce max rounds
orchestrator:
  max_round_count: 15  # Lower from 30

# Use slower model tiers
agent:
  model: gpt-4o-mini  # Has higher rate limits
```

**Future:** Automatic retry with exponential backoff planned.

---

### Memory Context Window

**Issue:** Long workflows may exceed model context windows, losing early context.

**Status:** ⚠️ Inherent limitation

**Impact:** Very long conversations may forget early details.

**Workaround:**
- Use Mem0 memory for persistent context
- Keep tasks focused and bounded
- Use checkpoints to segment long workflows

---

## Current Limitations

### Model Support

**Limitation:** Only OpenAI and Azure OpenAI models supported.

**Alternatives:** None currently

**Future:** May add support for:
- Anthropic Claude
- Google Gemini
- Open-source models (Ollama, vLLM)

---

### Tool Sandbox

**Limitation:** Code execution sandbox is Python-only with limited protection.

**Security Considerations:**
- Don't execute untrusted code
- Review code before approval in HITL
- Whitelist allowed modules
- Consider container isolation

**Configuration:**
```yaml
tools:
  - name: code_interpreter_tool
    config:
      allowed_modules:
        - math
        - json
        - datetime
      # NO network, file system access by default
```

---

### Concurrent Workflows

**Limitation:** CLI runs one workflow at a time.

**Workaround:** Use the REST API for concurrent execution via web interface.

---

### Streaming in Tests

**Limitation:** Streaming responses don't work well in automated tests.

**Workaround:** Tests disable streaming:
```python
@pytest.fixture
def no_streaming(monkeypatch):
    monkeypatch.setenv("STREAM_RESPONSES", "false")
```

---

### Memory Storage

**Limitation:** Mem0 requires Azure AI Search for vector storage.

**Impact:** Can't use memory features without Azure subscription.

**Alternatives:**
- Use in-memory context (no persistence)
- File-based checkpoints (no semantic search)

**Future:** Support for alternative vector stores:
- Chroma
- Pinecone
- Qdrant
- Local embeddings

---

## Workarounds & Solutions

### Reduce API Costs

Current cost reduction strategies:

```yaml
# 1. Shorter workflows
orchestrator:
  max_round_count: 15

# 2. Cheaper models
agent:
  model: gpt-4o-mini  # vs gpt-5

# 3. Lower temperature
temperature: 0.1  # More deterministic

# 4. Disable streaming
stream: false
```

### Improve Performance

```yaml
# 1. Reduce stall detection
orchestrator:
  max_stall_count: 2  # Faster replanning

# 2. Limit token output
agent:
  max_tokens: 2048  # vs 4096

# 3. Use faster models
model: gpt-4o  # vs o1-preview
```

### Enhance Reliability

```yaml
# 1. Enable checkpointing
checkpointing:
  enabled: true
  auto_save: true

# 2. Add approval gates
human_in_the_loop:
  enabled: true
  require_approval_for:
    - code_execution

# 3. Monitor with tracing
ENABLE_OTEL=true
```

---

## Reporting Issues

### Before Reporting

1. Check this document
2. Search [existing issues](https://github.com/Qredence/agentic-fleet/issues)
3. Review [troubleshooting guide](../runbooks/troubleshooting.md)
4. Check [FAQ](faq.md)

### When Reporting

Include:

```markdown
**Environment:**
- AgenticFleet version: 0.5.3
- Python version: 3.12.x
- OS: macOS / Linux / Windows
- uv version: x.x.x

**Description:**
Clear description of the issue

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. ...

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Logs:**
```
Relevant log snippets from logs/agenticfleet.log
```

**Configuration:**
Any relevant config settings
```

---

## Planned Improvements

### Short Term (Next Release)

- [ ] Real web search integration
- [ ] Retry logic for rate limits
- [ ] Better Windows support
- [ ] Local model support (experimental)

### Medium Term

- [ ] Additional model providers
- [ ] Alternative vector stores
- [ ] Container-based code sandbox
- [ ] Concurrent workflow execution in CLI
- [ ] Enhanced streaming in tests

### Long Term

- [ ] Distributed execution
- [ ] Agent marketplace
- [ ] Visual workflow builder
- [ ] Production deployment templates

---

## Version History

### v0.5.3 (Current)
- ✅ Fixed E2E test exclusion in CI
- ✅ Corrected checkpoint timestamp test
- ✅ Improved documentation structure

### v0.5.2
- ✅ Redis integration
- ✅ Chat history persistence
- ✅ Web HITL interface

### v0.5.1
- ✅ Magentic Fleet GA
- ✅ Observability integration
- ✅ Enhanced callbacks

### v0.5.0
- ✅ HITL implementation
- ✅ Checkpointing system
- ✅ Package restructure

See [Releases](../releases/) for detailed changelog.

---

**Found a new issue?** [Report it](https://github.com/Qredence/agentic-fleet/issues/new) with the template above.

**Have a workaround?** Share in [Discussions](https://github.com/Qredence/agentic-fleet/discussions).
