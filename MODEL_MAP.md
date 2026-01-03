# Model Map

This repo routes LLM calls through provider SDKs (no LiteLLM proxy):

- **DeepInfra (OpenAI‑compatible)** via `openai` SDK
- **Gemini** via `google-genai`
- **GLM‑4.7 (ZAI Anthropic‑compatible)** via `anthropic` SDK + `ZAI_ANTHROPIC_BASE_URL`

Model selection happens per agent role via env vars (`FLEET_MODEL_ROUTER|PLANNER|WORKER|JUDGE`), and the aliases below are normalized in `src/agentic_fleet/llm.py` (`MODEL_ALIASES`, `resolve_model_name()`).

## Alias → Provider Model

| Fleet alias (env value) | Provider | SDK | Resolved model name | Required env |
|---|---|---|---|---|
| `deepseek-v3.2` | DeepInfra | `openai` | `deepseek-ai/DeepSeek-V3.2` | `DEEPINFRA_API_KEY` (optional `DEEPINFRA_API_BASE_URL`) |
| `nemotron-30b` | DeepInfra | `openai` | `nvidia/Nemotron-3-Nano-30B-A3B` | `DEEPINFRA_API_KEY` (optional `DEEPINFRA_API_BASE_URL`) |
| `gemini-3-flash` | Gemini | `google-genai` | `gemini-3-flash-preview` | `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) |
| `gemini-3-pro` | Gemini | `google-genai` | `gemini-3-pro-preview` | `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) |
| `glm-4.7` | ZAI Anthropic | `anthropic` | `glm-4.7` (or `ZAI_MODEL_NAME`) | `ZAI_API_KEY`, `ZAI_ANTHROPIC_BASE_URL` |

Notes
- You can also set **direct provider model IDs** in `FLEET_MODEL_*` (e.g. `deepseek-ai/DeepSeek-V3.2` or `models/gemini-3-flash-preview`).
- Gemini “preview” models are the ones returned by `google-genai` model listing in this environment.

## Quick config examples

```bash
# from agentic-fleet/

# DeepInfra worker
export FLEET_MODEL_WORKER="deepseek-v3.2"

# Gemini worker
export FLEET_MODEL_WORKER="gemini-3-flash"

# GLM judge
export FLEET_MODEL_JUDGE="glm-4.7"
```

