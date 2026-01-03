"""LLM routing and caching for DSPy using provider SDKs."""

from __future__ import annotations

import os
from typing import Any, Iterable

from dspy.clients.base_lm import BaseLM

_DEFAULT_MODEL = os.getenv("DSPY_MODEL", "deepseek-v3.2")

DEFAULT_MODEL_ALIASES: dict[str, str] = {
    "router": os.getenv("FLEET_MODEL_ROUTER", _DEFAULT_MODEL),
    "planner": os.getenv("FLEET_MODEL_PLANNER", _DEFAULT_MODEL),
    "worker": os.getenv("FLEET_MODEL_WORKER", "gemini-3-flash"),
    "judge": os.getenv("FLEET_MODEL_JUDGE", _DEFAULT_MODEL),
    "default": _DEFAULT_MODEL,
}

_LM_CACHE: dict[tuple[Any, ...], BaseLM] = {}

_GEMINI_PREFIXES = ("gemini",)
_ANTHROPIC_PREFIXES = ("glm",)

_OPENAI_CLIENTS: dict[tuple[str, str], Any] = {}
_GOOGLE_CLIENTS: dict[str | None, Any] = {}
_ANTHROPIC_CLIENTS: dict[tuple[str, str], Any] = {}

# Canonical alias mapping. Keep these stable; override per-role via env vars.
MODEL_ALIASES: dict[str, str] = {
    # DeepInfra (OpenAI-compatible)
    "deepseek-v3.2": "deepseek-ai/DeepSeek-V3.2",
    "nemotron-30b": "nvidia/Nemotron-3-Nano-30B-A3B",
    # Gemini (google-genai)
    "gemini-3-flash": "gemini-3-flash-preview",
    "gemini-3-pro": "gemini-3-pro-preview",
    # ZAI (Anthropic-compatible)
    "glm-4.7": os.getenv("ZAI_MODEL_NAME", "glm-4.7"),
}


def resolve_model_alias(role: str, team_id: str | None = None) -> str:
    role_key = role.lower()
    if team_id:
        env_team_role = os.getenv(f"FLEET_MODEL_{team_id.upper()}_{role.upper()}")
        if env_team_role:
            return env_team_role
    env_role = os.getenv(f"FLEET_MODEL_{role.upper()}")
    if env_role:
        return env_role
    return DEFAULT_MODEL_ALIASES.get(role_key, DEFAULT_MODEL_ALIASES["default"])


def _resolve_provider(model: str) -> str:
    lowered = model.lower()
    if lowered.startswith("models/gemini") or lowered.startswith("models/gemma"):
        return "gemini"
    if any(lowered.startswith(prefix) for prefix in _GEMINI_PREFIXES):
        return "gemini"
    if any(lowered.startswith(prefix) for prefix in _ANTHROPIC_PREFIXES):
        return "anthropic"
    zai_model = os.getenv("ZAI_MODEL_NAME", "").lower()
    if zai_model and lowered == zai_model:
        return "anthropic"
    return "openai"


def resolve_model_name(model: str) -> str:
    resolved = MODEL_ALIASES.get(model, model)
    return resolved


def _normalize_messages(prompt: str | None, messages: Any) -> list[dict[str, str]]:
    if messages is None:
        if prompt is None:
            return []
        return [{"role": "user", "content": str(prompt)}]
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    if isinstance(messages, dict):
        return [_normalize_message(messages)]
    if isinstance(messages, Iterable):
        return [_normalize_message(item) for item in messages]
    return [_normalize_message(messages)]


def _normalize_message(message: Any) -> dict[str, str]:
    if isinstance(message, dict):
        role = message.get("role", "user")
        content = message.get("content") or message.get("text") or ""
        return {"role": str(role), "content": str(content)}
    if hasattr(message, "role"):
        role = getattr(message, "role")
        if hasattr(role, "value"):
            role = role.value
        content = getattr(message, "text", None) or getattr(message, "content", None) or ""
        return {"role": str(role), "content": str(content)}
    if hasattr(message, "text"):
        return {"role": "user", "content": str(getattr(message, "text"))}
    if hasattr(message, "content"):
        return {"role": "user", "content": str(getattr(message, "content"))}
    return {"role": "user", "content": str(message)}


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    chunks = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            chunks.append(f"{role}: {content}")
    return "\n".join(chunks).strip()


class _SimpleMessage:
    def __init__(self, content: str):
        self.content = content


class _SimpleChoice:
    def __init__(self, content: str):
        self.message = _SimpleMessage(content)


class _SimpleResponse:
    def __init__(self, content: str, model: str):
        self.choices = [_SimpleChoice(content)]
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.model = model


class FleetLM(BaseLM):
    """DSPy-compatible LM that routes to provider SDKs."""

    def __init__(self, model: str, provider: str | None = None, **kwargs: Any):
        super().__init__(model=model, model_type="chat", **kwargs)
        self.provider = provider or _resolve_provider(model)

    def forward(self, prompt: str | None = None, messages: Any = None, **kwargs: Any):
        merged = {**self.kwargs, **kwargs}
        temperature = merged.get("temperature")
        max_tokens = merged.get("max_tokens")
        normalized_messages = _normalize_messages(prompt, messages)
        if not normalized_messages:
            normalized_messages = [{"role": "user", "content": ""}]

        model_name = resolve_model_name(self.model)
        if self.provider == "gemini":
            return self._forward_gemini(model_name, normalized_messages, temperature, max_tokens)
        if self.provider == "anthropic":
            return self._forward_anthropic(model_name, normalized_messages, temperature, max_tokens)
        return self._forward_openai(model_name, normalized_messages, temperature, max_tokens)

    def _forward_openai(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
    ):
        from openai import OpenAI

        api_key = os.getenv("DEEPINFRA_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing DEEPINFRA_API_KEY for DeepInfra OpenAI-compatible calls.")
        base_url = os.getenv("DEEPINFRA_API_BASE_URL", "https://api.deepinfra.com/v1/openai")
        cache_key = (api_key, base_url)
        client = _OPENAI_CLIENTS.get(cache_key)
        if client is None:
            client = OpenAI(api_key=api_key, base_url=base_url)
            _OPENAI_CLIENTS[cache_key] = client

        params: dict[str, Any] = {"model": self.model, "messages": messages}
        params["model"] = model
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        return client.chat.completions.create(**params)

    def _forward_gemini(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
    ):
        from google import genai
        from google.genai import types as genai_types

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        client = _GOOGLE_CLIENTS.get(api_key)
        if client is None:
            client = genai.Client(api_key=api_key) if api_key else genai.Client()
            _GOOGLE_CLIENTS[api_key] = client

        prompt_text = _messages_to_prompt(messages)
        config_kwargs: dict[str, Any] = {}
        if temperature not in (None, 0, 0.0):
            config_kwargs["temperature"] = temperature
        if max_tokens is not None:
            config_kwargs["max_output_tokens"] = max_tokens
        config = genai_types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
        if config is None:
            response = client.models.generate_content(
                model=model,
                contents=prompt_text,
            )
        else:
            response = client.models.generate_content(
                model=model,
                contents=prompt_text,
                config=config,
            )

        text = getattr(response, "text", None)
        if text is None and getattr(response, "candidates", None):
            candidate = response.candidates[0]
            parts = (getattr(candidate.content, "parts", None) or []) if candidate else []
            text = "".join(getattr(part, "text", "") for part in parts)
        return _SimpleResponse(text or "", model)

    def _forward_anthropic(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
    ):
        import anthropic

        api_key = os.getenv("ZAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Missing ZAI_API_KEY for ZAI Anthropic-compatible calls.")
        base_url = os.getenv("ZAI_ANTHROPIC_BASE_URL")
        if not base_url:
            raise RuntimeError("Missing ZAI_ANTHROPIC_BASE_URL for ZAI Anthropic-compatible calls.")
        cache_key = (api_key, base_url)
        client = _ANTHROPIC_CLIENTS.get(cache_key)
        if client is None:
            client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
            _ANTHROPIC_CLIENTS[cache_key] = client

        params: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens or 1000}
        if temperature is not None:
            params["temperature"] = temperature
        response = client.messages.create(**params)

        text_blocks = getattr(response, "content", []) or []
        text = "".join(getattr(block, "text", "") for block in text_blocks)
        return _SimpleResponse(text, model)


def _cache_key_for_provider(provider: str, api_key: str | None, base_url: str | None) -> tuple[Any, ...]:
    return (provider, api_key or "", base_url or "")


def get_lm(*, model: str, temperature: float | None = None, max_tokens: int | None = None) -> BaseLM:
    if temperature is None:
        temperature = float(os.getenv("DSPY_TEMPERATURE", "0"))
    if max_tokens is None:
        max_tokens_env = os.getenv("DSPY_MAX_TOKENS")
        max_tokens = int(max_tokens_env) if max_tokens_env else None

    provider = _resolve_provider(model)
    if provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        cache_key = (model, temperature, max_tokens) + _cache_key_for_provider(provider, api_key, None)
    elif provider == "anthropic":
        api_key = os.getenv("ZAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        base_url = os.getenv("ZAI_ANTHROPIC_BASE_URL")
        cache_key = (model, temperature, max_tokens) + _cache_key_for_provider(provider, api_key, base_url)
    else:
        api_key = os.getenv("DEEPINFRA_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("DEEPINFRA_API_BASE_URL", "https://api.deepinfra.com/v1/openai")
        cache_key = (model, temperature, max_tokens) + _cache_key_for_provider(provider, api_key, base_url)

    cached = _LM_CACHE.get(cache_key)
    if cached is not None:
        return cached

    lm = FleetLM(model=model, provider=provider, temperature=temperature, max_tokens=max_tokens)
    _LM_CACHE[cache_key] = lm
    return lm
