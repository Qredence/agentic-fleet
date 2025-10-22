"""Structured tool registry with schema validation and retries.

This module provides:
- A @tool decorator to register callables with metadata (name, description, tags)
- Parameter validation via Pydantic models (with permissive coercion)
- Optional JSON Schema validation (best-effort if jsonschema is available)
- Central ToolRegistry for lookup and invocation
- Retry/backoff execution wrapper and basic timeout/size-cap helpers

The registry is designed to be lightweight and to work when the Microsoft Agent
Framework is unavailable (typical in tests). Agents can request callables from
this registry to avoid ad-hoc wiring.
"""

from __future__ import annotations

import functools
import subprocess
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from agenticfleet.core.exceptions import ToolExecutionError
from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)


# Optional jsonschema validation if library is present
try:  # pragma: no cover - optional dependency
    import jsonschema  # type: ignore

    _JSONSCHEMA_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    jsonschema = None  # type: ignore
    _JSONSCHEMA_AVAILABLE = False


class ToolValidationError(ToolExecutionError):
    """Raised when tool parameter validation fails."""


class ToolTimeoutError(ToolExecutionError):
    """Raised when a tool exceeds its configured timeout."""


@dataclass(frozen=True)
class RetryPolicy:
    """Retry/backoff configuration for tool execution."""

    max_attempts: int = 1
    backoff_strategy: str = "exponential"  # "exponential" or "constant"
    initial_delay: float = 0.5
    max_delay: float = 8.0
    jitter: bool = True

    def next_delay(self, attempt: int) -> float:
        if self.max_attempts <= 1:
            return 0.0
        base = self.initial_delay
        if self.backoff_strategy == "constant":
            delay = base
        else:
            delay = base * (2 ** (attempt - 1))
        if self.jitter:
            # Simple bounded jitter: 80%..120%
            delay *= 0.8 + (0.4 * (attempt % 3) / 2)
        return min(delay, self.max_delay)


@dataclass
class ToolMetadata:
    name: str
    description: str | None = None
    tags: set[str] = field(default_factory=set)
    timeout_seconds: float | None = None
    max_output_bytes: int | None = 64 * 1024  # default 64 KiB cap on output
    allow_coercion: bool = True
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    input_model: type[BaseModel] | None = None
    json_schema: dict[str, Any] | None = None


@dataclass
class _RegisteredTool:
    func: Callable[..., Any]
    meta: ToolMetadata


class ToolRegistry:
    """Central registry for validated, retried tool execution."""

    def __init__(self) -> None:
        self._tools: dict[str, _RegisteredTool] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        *,
        description: str | None = None,
        tags: Iterable[str] | None = None,
        timeout_seconds: float | None = None,
        max_output_bytes: int | None = None,
        allow_coercion: bool = True,
        retry_policy: RetryPolicy | None = None,
        input_model: type[BaseModel] | None = None,
        json_schema: dict[str, Any] | None = None,
    ) -> Callable[..., Any]:
        meta = ToolMetadata(
            name=name,
            description=description,
            tags=set(tags or ()),
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
            allow_coercion=allow_coercion,
            retry_policy=retry_policy or RetryPolicy(),
            input_model=input_model,
            json_schema=json_schema,
        )

        wrapped = self._wrap(func, meta)

        with self._lock:
            self._tools[name] = _RegisteredTool(func=wrapped, meta=meta)

        return wrapped

    def _wrap(self, func: Callable[..., Any], meta: ToolMetadata) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            params = kwargs
            # Validate via JSON Schema if provided (best effort)
            if meta.json_schema is not None and _JSONSCHEMA_AVAILABLE:
                try:  # type: ignore[union-attr]
                    jsonschema.validate(instance=params, schema=meta.json_schema)  # type: ignore[arg-type]
                except Exception as e:  # pragma: no cover - jsonschema optional
                    raise ToolValidationError(
                        f"JSON Schema validation failed for {meta.name}: {e}"
                    ) from e

            # Pydantic validation/coercion if model provided
            if meta.input_model is not None:
                try:
                    model_instance = meta.input_model(**params)
                    params = model_instance.model_dump()
                except ValidationError as ve:
                    raise ToolValidationError(
                        f"Parameter validation failed for {meta.name}: {ve.errors()}"
                    ) from ve

            attempt = 0
            last_error: Exception | None = None
            while True:
                attempt += 1
                try:
                    result = func(**params)
                    # Apply output size cap if configured
                    return _cap_output(result, meta.max_output_bytes)
                except ToolTimeoutError:
                    # Timeouts are not retried by default
                    raise
                except Exception as e:  # noqa: BLE001 - surface tool exceptions cleanly
                    last_error = e
                    if attempt >= max(1, meta.retry_policy.max_attempts):
                        break
                    delay = meta.retry_policy.next_delay(attempt)
                    if delay > 0:
                        time.sleep(delay)
                    continue

            # Exhausted retries
            raise ToolExecutionError(
                f"Tool '{meta.name}' failed after {attempt} attempts: {last_error}"
            ) from last_error

        # Attach registry metadata for discoverability
        setattr(wrapper, "_tool_meta", meta)
        return wrapper

    def get(self, name: str) -> Callable[..., Any]:
        try:
            return self._tools[name].func
        except KeyError as e:
            raise KeyError(f"No tool registered under name '{name}'") from e

    def get_metadata(self, name: str) -> ToolMetadata:
        try:
            return self._tools[name].meta
        except KeyError as e:
            raise KeyError(f"No tool registered under name '{name}'") from e

    def list(self, *, tags: Iterable[str] | None = None) -> dict[str, ToolMetadata]:
        if not tags:
            return {k: v.meta for k, v in self._tools.items()}
        wanted = set(tags)
        return {k: v.meta for k, v in self._tools.items() if v.meta.tags & wanted}

    def resolve_tools_from_config(
        self,
        tools_config: list[dict[str, Any]],
    ) -> list[Callable[..., Any]]:
        """Resolve callables from a typical agent tools config list.

        Each item should contain at least a 'name' and may include 'enabled'.
        Unknown tools are skipped to allow graceful fallback in agents.
        """
        resolved: list[Callable[..., Any]] = []
        for entry in tools_config or []:
            if not entry or not entry.get("enabled", True):
                continue
            name = entry.get("name")
            if not isinstance(name, str):
                continue
            try:
                resolved.append(self.get(name))
            except KeyError:
                logger.debug("Tool %s not found in registry; skipping", name)
        return resolved


# Global registry instance
registry = ToolRegistry()


def tool(
    *,
    name: str,
    input_model: type[BaseModel] | None = None,
    description: str | None = None,
    tags: Iterable[str] | None = None,
    timeout_seconds: float | None = None,
    max_output_bytes: int | None = None,
    retry_policy: RetryPolicy | None = None,
    json_schema: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register a callable in the global ToolRegistry.

    The wrapped function should accept keyword arguments matching the provided
    Pydantic ``input_model`` fields when one is specified.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return registry.register(
            name=name,
            func=func,
            description=description or (func.__doc__ or None),
            tags=tags,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
            allow_coercion=True,
            retry_policy=retry_policy,
            input_model=input_model,
            json_schema=json_schema,
        )

    return decorator


# -----------------------------
# Built-in IO-bound tools
# -----------------------------




class FSReadParams(BaseModel):
    path: str = Field(..., description="Path to a local text file to read")
    encoding: str = Field("utf-8", description="Text encoding for decoding bytes")
    max_bytes: int | None = Field(
        None, description="Optional per-call output cap in bytes (truncates if exceeded)"
    )


@tool(
    name="fs_read",
    input_model=FSReadParams,
    description="Read a small local text file with a size cap.",
    tags={"filesystem", "io"},
    timeout_seconds=5.0,
    max_output_bytes=64 * 1024,
    retry_policy=RetryPolicy(max_attempts=2, backoff_strategy="constant", initial_delay=0.0),
)
def fs_read(*, path: str, encoding: str = "utf-8", max_bytes: int | None = None) -> str:
    start = time.perf_counter()
    try:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        data = p.read_bytes()
        # Enforce the smaller of per-call and registry caps
        reg_cap = registry.get_metadata("fs_read").max_output_bytes
        cap = min([b for b in [max_bytes, reg_cap] if b is not None], default=None)
        if cap is not None and len(data) > cap:
            data = data[:cap]
        text = data.decode(encoding, errors="replace")
        return text
    except Exception as e:  # noqa: BLE001
        raise ToolExecutionError(f"fs_read failed: {e}") from e
    finally:
        # Simple timeout check – operations are bounded by disk speed; expose as timeout error
        timeout = registry.get_metadata("fs_read").timeout_seconds
        elapsed = time.perf_counter() - start
        if timeout is not None and elapsed > timeout:
            raise ToolTimeoutError(
                f"fs_read exceeded timeout of {timeout}s (elapsed {elapsed:.2f}s)"
            )




class HTTPFetchParams(BaseModel):
    url: HttpUrl = Field(..., description="URL to fetch using HTTP GET")
    headers: dict[str, str] | None = Field(None, description="Optional HTTP headers")
    max_bytes: int | None = Field(None, description="Optional maximum size of body to return")


@tool(
    name="http_fetch",
    input_model=HTTPFetchParams,
    description="Fetch a URL using HTTP GET with a response size cap.",
    tags={"web", "http", "io"},
    timeout_seconds=15.0,
    max_output_bytes=256 * 1024,
    retry_policy=RetryPolicy(max_attempts=2, backoff_strategy="exponential", initial_delay=0.2),
)
def http_fetch(
    *,
    url: HttpUrl,
    headers: dict[str, str] | None = None,
    max_bytes: int | None = None,
) -> str:
    meta = registry.get_metadata("http_fetch")
    timeout = meta.timeout_seconds or 15.0
    try:
        resp = requests.get(str(url), headers=headers or {}, timeout=timeout)
        resp.raise_for_status()
        content: bytes
        try:
            content = resp.content
        except Exception as e:  # pragma: no cover - requests interface
            raise ToolExecutionError(f"http_fetch: failed to read response body: {e}") from e
        cap = min([b for b in [max_bytes, meta.max_output_bytes] if b is not None], default=None)
        if cap is not None and len(content) > cap:
            content = content[:cap]
        # attempt text decoding using response encoding or utf-8 fallback
        encoding = resp.encoding or "utf-8"
        try:
            return content.decode(encoding, errors="replace")
        except Exception:
            return content.decode("utf-8", errors="replace")
    except requests.Timeout as e:  # pragma: no cover - requests may raise different errors
        raise ToolTimeoutError(f"http_fetch timeout after {timeout}s: {e}") from e
    except requests.RequestException as e:
        raise ToolExecutionError(f"http_fetch request failed: {e}") from e




class GitBranchParams(BaseModel):
    repo_path: str = Field(".", description="Path to the git repository")


@tool(
    name="git_current_branch",
    input_model=GitBranchParams,
    description="Return the current git branch name for a repository.",
    tags={"git", "io"},
    timeout_seconds=5.0,
    retry_policy=RetryPolicy(max_attempts=2, backoff_strategy="constant", initial_delay=0.0),
)
def git_current_branch(*, repo_path: str = ".") -> str:
    meta = registry.get_metadata("git_current_branch")
    try:
        cp = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=meta.timeout_seconds or 5.0,
        )
        return (cp.stdout or "").strip()
    except subprocess.TimeoutExpired as e:  # pragma: no cover - environment dependent
        raise ToolTimeoutError(f"git_current_branch timed out: {e}") from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise ToolExecutionError(f"git_current_branch failed: {stderr or e}") from e


# Helper to cap output size for text/bytes payloads only.

def _cap_output(result: Any, cap: int | None) -> Any:
    if cap is None:
        return result
    try:
        if isinstance(result, str):
            return result[:cap]
        if isinstance(result, (bytes, bytearray)):
            return result[:cap]
    except Exception:
        return result

    # Non-text results (e.g., Pydantic models, dicts, custom objects) should
    # pass through unchanged so callers preserve structure and typing.
    return result
