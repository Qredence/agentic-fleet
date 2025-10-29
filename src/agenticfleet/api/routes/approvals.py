from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, JSONResponse, Request, status
from sqlalchemy.orm import Session

from agenticfleet.api.models.approval import ApprovalResponse
from agenticfleet.persistance.database import ApprovalRequest, ApprovalStatus, get_db

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])
LOGGER = logging.getLogger(__name__)


@router.post("")
async def create_approval_request(
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:  # pragma: no cover - defensive guard for malformed JSON
        data = {}
    approval_request = ApprovalRequest(
        request_id=str(uuid4()),
        conversation_id=data.get("conversation_id"),
        details=data.get("details"),
    )
    db.add(approval_request)
    db.commit()
    db.refresh(approval_request)
    LOGGER.info(
        "SSE Event: approval.requested request_id=%s conversation_id=%s",
        approval_request.request_id,
        approval_request.conversation_id,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"request_id": approval_request.request_id},
    )


@router.get("")
async def list_pending_approvals(
    db: Session = Depends(get_db),  # noqa: B008
) -> JSONResponse:
    pending_approvals = (
        db.query(ApprovalRequest).filter(ApprovalRequest.status == ApprovalStatus.PENDING).all()
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=[{"request_id": ar.request_id, "details": ar.details} for ar in pending_approvals],
    )


@router.post("/{request_id}")
async def respond_to_approval_request(
    request_id: str,
    response: ApprovalResponse,
    db: Session = Depends(get_db),  # noqa: B008
) -> JSONResponse:
    approval_request = (
        db.query(ApprovalRequest).filter(ApprovalRequest.request_id == request_id).first()
    )
    if not approval_request:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Approval request not found"},
        )

    decision_details = dict(approval_request.details or {})
    if response.reason:
        decision_details["decision_reason"] = response.reason
    if response.modified_code:
        decision_details["modified_code"] = response.modified_code
    if response.modified_params:
        decision_details["modified_params"] = response.modified_params

    if response.decision == "approved":
        approval_request.status = ApprovalStatus.APPROVED
    elif response.decision == "rejected":
        approval_request.status = ApprovalStatus.REJECTED
    elif response.decision == "modified":
        approval_request.status = ApprovalStatus.APPROVED
        decision_details["decision"] = "modified"

    approval_request.details = decision_details
    db.commit()

    LOGGER.info(
        "SSE Event: approval.responded request_id=%s status=%s",
        request_id,
        approval_request.status,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": approval_request.status.value,
            "decision": response.decision,
            "details": decision_details,
        },
    )
