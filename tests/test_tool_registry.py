import os
import tempfile

import pytest
from pydantic import BaseModel, Field

from agenticfleet.tools.tool_calling import (
    RetryPolicy,
    ToolValidationError,
    registry,
    tool,
)


def test_fs_read_success() -> None:
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp.write("hello world")
        tmp_path = tmp.name
    try:
        result = registry.get("fs_read")(path=tmp_path)
        assert isinstance(result, str)
        assert "hello world" in result
    finally:
        os.unlink(tmp_path)


def test_http_fetch_validation_failure() -> None:
    # Invalid URL should trigger pydantic validation via ToolValidationError
    with pytest.raises(ToolValidationError):
        registry.get("http_fetch")(url="not-a-url")  # type: ignore[arg-type]


def test_retry_exhaustion_with_fake_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    class Params(BaseModel):
        n: int = Field(...)

    calls: dict[str, int] = {"count": 0}

    @tool(
        name="flaky_fake",
        input_model=Params,
        retry_policy=RetryPolicy(
            max_attempts=3,
            initial_delay=0.0,
            backoff_strategy="constant",
            jitter=False,
        ),
    )
    def flaky_fake(*, n: int) -> int:  # noqa: F841 - used by registry registration
        calls["count"] += 1
        raise RuntimeError("boom")

    with pytest.raises(Exception) as exc:
        registry.get("flaky_fake")(n=1)

    # Should have attempted exactly 3 times
    assert calls["count"] == 3
    assert "failed" in str(exc.value).lower() or "boom" in str(exc.value).lower()
