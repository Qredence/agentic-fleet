from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ApprovalDecision(BaseModel):
    decision: str  # "approve" | "deny"
    reason: str | None = None


@router.post("/approvals/{request_id}")
def submit_approval(request_id: str, decision: ApprovalDecision) -> dict:
    # Stub: persist decision later; emit event to stream
    return {"request_id": request_id, "status": "received", "decision": decision.decision}
