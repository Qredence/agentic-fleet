# Troubleshooting & Runbooks

Collected fixes and checklists for recurring operational issues.

## GitHub Environment Tag Pattern
**Symptom:** Creating a deployment rule for the `pypi` environment returns “Name is invalid”.

**Resolution:**
```
v[0-9]+.[0-9]+.[0-9]+    # production releases
v[0-9]+.[0-9]+.[0-9]+*   # allow pre-releases such as v0.5.0-alpha1
```
Add the rule under _Settings ▸ Environments ▸ pypi ▸ Deployment branches and tags_. Avoid glob syntax such as `v*.*.*`; GitHub requires the bracket/regex-style pattern above.

## ChatAgent Temperature Errors
**Symptom:** `400` response: `Unsupported parameter: 'temperature' is not supported with this model`.

**Root cause:** `ChatAgent` (Microsoft Agent Framework) does not accept a `temperature` keyword.

**Fix:**
```python
agent = ChatAgent(
    chat_client=client,
    instructions=config.get("system_prompt", ""),
    name=agent_config.get("name", "orchestrator"),
)
```
Retain temperature values in YAML configs for future runtime options, but do not pass them into the constructor.

## Mem0ContextProvider Regression Suite
- 21 pytest cases cover init, get, add, and configuration branches.
- Run with `uv run pytest tests/test_mem0_context_provider.py -v`.
- Fixtures mock Azure endpoints, the `Memory` vector store, and `AzureOpenAI` client, ensuring no live calls occur.

## Historical Fix Log (October 10, 2025)
1. Corrected `dependency-groups` typo in `pyproject.toml`.
2. Migrated all agents/workflows to `OpenAIResponsesClient`.
3. Normalised UV dependency group syntax to silence deprecation warnings.
4. Repaired `pyproject.toml` and workflow wiring for UV-based packaging.
