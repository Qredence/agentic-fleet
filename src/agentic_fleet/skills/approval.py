"""HITL (Human-in-the-Loop) approval workflow for skill creation.

This module handles the approval process for new skills, including
request serialization, review interface, and decision handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agentic_fleet.skills.creator import SkillApprovalRequest


class ApprovalStatus(str, Enum):
    """Status of a skill approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class ApprovalDecision(BaseModel):
    """Human decision on skill approval."""

    status: ApprovalStatus
    feedback: str = Field(default="", description="Reason for rejection or revision request")
    revisions: dict[str, Any] | None = Field(
        default=None, description="Specific revisions requested"
    )
    reviewed_by: str = Field(default="human", description="Who reviewed")
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


class SkillApprovalWorkflow(BaseModel):
    """Workflow for managing skill approval lifecycle."""

    request: SkillApprovalRequest
    decision: ApprovalDecision | None = None
    workflow_id: str = Field(default_factory=lambda: f"skill-approval-{datetime.utcnow().isoformat()}")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def submit_for_review(self) -> dict[str, Any]:
        """Submit the skill for human review."""
        self.updated_at = datetime.utcnow()
        return {
            "workflow_id": self.workflow_id,
            "status": ApprovalStatus.PENDING.value,
            "request": self.request.model_dump(),
            "created_at": self.created_at.isoformat(),
        }

    def make_decision(self, decision: ApprovalDecision) -> dict[str, Any]:
        """Record a human decision on this skill."""
        self.decision = decision
        self.updated_at = datetime.utcnow()
        return {
            "workflow_id": self.workflow_id,
            "status": decision.status.value,
            "decision": decision.model_dump(),
            "updated_at": self.updated_at.isoformat(),
        }

    def is_pending(self) -> bool:
        """Check if the workflow is still pending review."""
        return self.decision is None

    def is_approved(self) -> bool:
        """Check if the skill has been approved."""
        return self.decision is not None and self.decision.status == ApprovalStatus.APPROVED

    def is_rejected(self) -> bool:
        """Check if the skill has been rejected."""
        return self.decision is not None and self.decision.status == ApprovalStatus.REJECTED

    def needs_revision(self) -> bool:
        """Check if revision was requested."""
        return (
            self.decision is not None
            and self.decision.status == ApprovalStatus.REVISION_REQUESTED
        )


# =============================================================================
# Approval Store (in-memory for now, can be extended to DB)
# =============================================================================

class ApprovalStore:
    """In-memory store for approval workflows."""

    def __init__(self):
        self._workflows: dict[str, SkillApprovalWorkflow] = {}

    def create_workflow(self, request: SkillApprovalRequest) -> str:
        """Create a new approval workflow and return its ID."""
        workflow = SkillApprovalWorkflow(request=request)
        self._workflows[workflow.workflow_id] = workflow
        return workflow.workflow_id

    def get_workflow(self, workflow_id: str) -> SkillApprovalWorkflow | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_pending(self) -> list[SkillApprovalWorkflow]:
        """List all pending approval workflows."""
        return [w for w in self._workflows.values() if w.is_pending()]

    def list_all(self) -> list[SkillApprovalWorkflow]:
        """List all approval workflows."""
        return list(self._workflows.values())

    def record_decision(
        self,
        workflow_id: str,
        status: ApprovalStatus,
        feedback: str = "",
        revisions: dict[str, Any] | None = None,
        reviewed_by: str = "human",
    ) -> bool:
        """Record a decision for a workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return False

        decision = ApprovalDecision(
            status=status,
            feedback=feedback,
            revisions=revisions,
            reviewed_by=reviewed_by,
        )
        workflow.make_decision(decision)
        return True

    def count_by_status(self) -> dict[str, int]:
        """Count workflows by status."""
        counts: dict[str, int] = {
            ApprovalStatus.PENDING.value: 0,
            ApprovalStatus.APPROVED.value: 0,
            ApprovalStatus.REJECTED.value: 0,
            ApprovalStatus.REVISION_REQUESTED.value: 0,
        }
        for workflow in self._workflows.values():
            if workflow.decision is None:
                counts[ApprovalStatus.PENDING.value] += 1
            else:
                counts[workflow.decision.status.value] += 1
        return counts


# Global approval store instance
approval_store = ApprovalStore()
