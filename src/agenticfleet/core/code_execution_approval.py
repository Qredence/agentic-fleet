"""Utilities for requesting approval before executing code."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from agenticfleet.core.approval import ApprovalDecision
from agenticfleet.core.approved_tools import get_approval_handler
from agenticfleet.core.cli_approval import create_approval_request
from agenticfleet.core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    pass

logger = get_logger(__name__)


def maybe_request_approval_for_code_execution(
    code: str, language: str
) -> str | "CodeExecutionResult" | None:
    """Request approval for executing code if an approval handler is configured.

    Args:
        code: Code that is scheduled for execution.
        language: Programming language of the code.

    Returns:
        ``None`` if no approval handler is configured or approval is granted without
        modifications.
        ``str`` with the modified code if the approval handler returns a modified
        version of the code.
        ``CodeExecutionResult`` if the approval is rejected or times out so the
        caller can surface the failure to the agent.
    """

    handler = get_approval_handler()
    if handler is None:
        return None

    request = create_approval_request(
        operation_type="code_execution",
        agent_name="coder",
        operation="Execute Python code",
        details={"language": language, "code_length": len(code)},
        code=code,
    )

    async def _request_approval() -> str | "CodeExecutionResult" | None:
        response = await handler.request_approval(request)

        if response.decision == ApprovalDecision.APPROVED:
            logger.info("Code execution approved: %s", request.request_id)
            return None

        if response.decision == ApprovalDecision.MODIFIED:
            logger.info(
                "Code execution approved with modifications: %s", request.request_id
            )
            return response.modified_code or code

        logger.warning(
            "Code execution %s: %s",
            response.decision.value,
            request.request_id,
        )
        reason = response.reason or f"Operation {response.decision.value}"
        from agenticfleet.agents.coder.tools.code_interpreter import CodeExecutionResult

        return CodeExecutionResult(
            success=False,
            output="",
            error=f"Code execution was {response.decision.value}: {reason}",
            execution_time=0.0,
            language=language,
            exit_code=1,
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
            return None
        return loop.run_until_complete(_request_approval())

    return asyncio.run(_request_approval())
