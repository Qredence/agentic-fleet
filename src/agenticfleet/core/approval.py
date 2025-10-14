"""Human-in-the-Loop approval system for AgenticFleet.

This module provides interfaces and models for implementing human approval
for sensitive operations like code execution and data modifications.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalDecision(str, Enum):
    """Decision made on an approval request."""

    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    TIMEOUT = "timeout"


class ApprovalRequest(BaseModel):
    """Request for human approval of an operation."""

    request_id: str = Field(..., description="Unique identifier for this request")
    operation_type: str = Field(..., description="Type of operation requiring approval")
    agent_name: str = Field(..., description="Name of the agent requesting approval")
    operation: str = Field(..., description="Description of the operation")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional details about the operation"
    )
    code: str | None = Field(None, description="Code to be executed (if applicable)")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO timestamp of request",
    )


class ApprovalResponse(BaseModel):
    """Response to an approval request."""

    request_id: str = Field(..., description="ID of the request being responded to")
    decision: ApprovalDecision = Field(..., description="Approval decision")
    modified_code: str | None = Field(None, description="Modified code if decision is MODIFIED")
    reason: str | None = Field(None, description="Reason for rejection or modification")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO timestamp of response",
    )


class ApprovalHandler(ABC):
    """Abstract base class for approval handlers.

    Implementations can provide different UI/UX for approval requests,
    such as CLI prompts, web interfaces, or automated policies.
    """

    @abstractmethod
    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """
        Request approval for an operation.

        Args:
            request: The approval request with operation details

        Returns:
            ApprovalResponse: The user's decision and any modifications
        """
        pass

    def should_require_approval(self, operation_type: str, enabled_operations: list[str]) -> bool:
        """
        Check if an operation type requires approval based on configuration.

        Args:
            operation_type: Type of operation to check
            enabled_operations: List of operation types that require approval

        Returns:
            bool: True if approval is required
        """
        return operation_type in enabled_operations
