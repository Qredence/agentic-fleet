"""Utilities for requesting approval before executing code."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple

from agenticfleet.core.approval import ApprovalDecision
from agenticfleet.core.approved_tools import (
    get_approval_handler,
    operation_requires_approval,
)
from agenticfleet.core.cli_approval import create_approval_request
from agenticfleet.core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from agenticfleet.core.code_types import CodeExecutionResult

logger = get_logger(__name__)


class CodeApprovalOutcome(Enum):
    NO_HANDLER = "no_handler"
    APPROVED = "approved"
    MODIFIED = "modified"
    REJECTED = "rejected"


class CodeApprovalResult(NamedTuple):
    outcome: CodeApprovalOutcome
    modified_code: str | None = None
    execution_result: CodeExecutionResult | None = None


def maybe_request_approval_for_code_execution(code: str, language: str) -> CodeApprovalResult:
    """Request approval for executing code if an approval handler is configured.

    Args:
        code: Code that is scheduled for execution.
        language: Programming language of the code.

    Returns:
        CodeApprovalResult indicating the outcome and any relevant data.
    """

    operation_type = "code_execution"
    handler = get_approval_handler()
    if handler is None:
        return CodeApprovalResult(outcome=CodeApprovalOutcome.NO_HANDLER)

    if not operation_requires_approval(operation_type):
        return CodeApprovalResult(outcome=CodeApprovalOutcome.APPROVED)

    request = create_approval_request(
        operation_type=operation_type,
        agent_name="coder",
        operation="Execute Python code",
        details={"language": language, "code_length": len(code)},
        code=code,
    )

    async def _request_approval() -> CodeApprovalResult:
        response = await handler.request_approval(request)

        if response.decision == ApprovalDecision.APPROVED:
            logger.info("Code execution approved: %s", request.request_id)
            return CodeApprovalResult(outcome=CodeApprovalOutcome.APPROVED)

        if response.decision == ApprovalDecision.MODIFIED:
            logger.info("Code execution approved with modifications: %s", request.request_id)
            return CodeApprovalResult(
                outcome=CodeApprovalOutcome.MODIFIED,
                modified_code=response.modified_code or code,
            )

        logger.warning(
            "Code execution %s: %s",
            response.decision.value,
            request.request_id,
        )
        reason = response.reason or f"Operation {response.decision.value}"
        from agenticfleet.core.code_types import CodeExecutionResult

        return CodeApprovalResult(
            outcome=CodeApprovalOutcome.REJECTED,
            execution_result=CodeExecutionResult(
                success=False,
                output="",
                error=f"Code execution was {response.decision.value}: {reason}",
                execution_time=0.0,
                language=language,
                exit_code=1,
            ),
        )

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        if loop.is_running():
            logger.warning(
                "Approval handler is set but tool was called synchronously in running "
                "loop. Executing without approval."
            )
            return CodeApprovalResult(outcome=CodeApprovalOutcome.APPROVED)
        return loop.run_until_complete(_request_approval())

    return asyncio.run(_request_approval())
