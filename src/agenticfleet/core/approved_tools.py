"""Code interpreter tool with human-in-the-loop approval support."""

from typing import Any

# (Import removed to break cyclic import. See function-local imports below.)
from agenticfleet.core.approval import ApprovalDecision, ApprovalHandler
from agenticfleet.core.cli_approval import create_approval_request
from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)

# Global approval handler (set by workflow)
_approval_handler: ApprovalHandler | None = None


def set_approval_handler(handler: ApprovalHandler | None) -> None:
    """
    Set the global approval handler for code execution.

    Args:
        handler: Approval handler instance or None to disable approval
    """
    global _approval_handler
    _approval_handler = handler
    logger.info(
        f"Approval handler {'set' if handler else 'disabled'} for code execution"
    )


def get_approval_handler() -> ApprovalHandler | None:
    """
    Get the current approval handler.

    Returns:
        Current approval handler or None
    """
    return _approval_handler


async def code_interpreter_tool_with_approval(
    code: str, language: str = "python"
) -> "CodeExecutionResult":
    """
    Execute code with human-in-the-loop approval if enabled.

    from agenticfleet.agents.coder.tools.code_interpreter import (
        CodeExecutionResult,
        code_interpreter_tool as _original_code_interpreter,
    )
    Args:
        code: The code to execute
        language: Programming language (currently supports python)

    Returns:
        CodeExecutionResult: Structured execution results with success status and outputs
    """
    handler = get_approval_handler()

    # If no handler is set, execute directly
    if handler is None:
        return _original_code_interpreter(code, language)

    # Create approval request
    request = create_approval_request(
        operation_type="code_execution",
        agent_name="coder",
        operation="Execute Python code",
        details={"language": language, "code_length": len(code)},
        code=code,
    )

    # Request approval
    logger.info(f"Requesting approval for code execution: {request.request_id}")
    response = await handler.request_approval(request)

    # Handle approval decision
    if response.decision == ApprovalDecision.APPROVED:
        logger.info(f"Code execution approved: {request.request_id}")
        return _original_code_interpreter(code, language)

    elif response.decision == ApprovalDecision.MODIFIED:
        logger.info(
            f"Code execution approved with modifications: {request.request_id}"
        )
        modified_code = response.modified_code or code
        return _original_code_interpreter(modified_code, language)

    else:  # REJECTED or TIMEOUT
        logger.warning(
            f"Code execution {response.decision.value}: {request.request_id}"
        )
        reason = response.reason or f"Operation {response.decision.value}"
        return CodeExecutionResult(
            success=False,
            output="",
            error=f"Code execution was {response.decision.value}: {reason}",
            execution_time=0.0,
            language=language,
            exit_code=1,
        )


# For synchronous contexts, provide a sync wrapper
def code_interpreter_tool(code: str, language: str = "python") -> "CodeExecutionResult":
    """
    Synchronous wrapper for code execution with approval.

    This is used when the agent framework calls tools synchronously.
    If approval is needed, it will be skipped with a warning.

    Args:
        code: The code to execute
        language: Programming language (currently supports python)

    Returns:
    from agenticfleet.agents.coder.tools.code_interpreter import (
        CodeExecutionResult,
        code_interpreter_tool as _original_code_interpreter,
    )
        CodeExecutionResult: Structured execution results
    """
    import asyncio

    handler = get_approval_handler()

    # If no handler, execute directly
    if handler is None:
        return _original_code_interpreter(code, language)

    # Try to run async approval in current event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use asyncio.run
            # Log a warning and execute directly
            logger.warning(
                "Approval handler is set but tool was called synchronously in running loop. "
                "Executing without approval."
            )
            return _original_code_interpreter(code, language)
        else:
            # No running loop, we can run the async function
            return loop.run_until_complete(
                code_interpreter_tool_with_approval(code, language)
            )
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(code_interpreter_tool_with_approval(code, language))
