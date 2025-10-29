from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ApprovalResponse(BaseModel):
    """Typed payload returned by the approval UI."""

    decision: Literal["approved", "rejected", "modified"]
    reason: str | None = None
    modified_code: str | None = None
    modified_params: dict[str, Any] | None = None
